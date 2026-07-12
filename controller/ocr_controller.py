"""Conecta los eventos de la vista con la lógica del Model."""

import os
import time

from PIL import Image, ImageOps
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QEvent, QObject, QThread, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox

from model.config_model import save_tesseract_path
from model.ocr_model import transcribe_large_image
from model.tesseract_locator import resolve_tesseract_path
from view.ocr_view import OcrView

COUNTER_INTERVAL_MS = 200
PREVIEW_RESIZE_DEBOUNCE_MS = 120

LANGUAGE_MAP = {
    "Español": "spa",
    "Inglés": "eng",
    "Ambos": "spa+eng",
}


class TranscriptionWorker(QThread):
    """Corre `transcribe_large_image` en un hilo aparte y emite el resultado por señal."""

    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, image_path: str, language_code: str, tesseract_path: str | None, parent: QObject | None = None) -> None:
        """Guarda los parámetros de la transcripción a ejecutar en `run()`."""
        super().__init__(parent)
        self.image_path = image_path
        self.language_code = language_code
        self.tesseract_path = tesseract_path

    def run(self) -> None:
        """Ejecuta la transcripción y emite `succeeded` o `failed` según el resultado."""
        try:
            result = transcribe_large_image(self.image_path, self.language_code, self.tesseract_path)
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.succeeded.emit(result)


class AppState:
    """Estado en memoria de la app mientras está abierta (no persistido)."""

    def __init__(self) -> None:
        self.image_path: str | None = None
        self.selected_language: str = "Ambos"
        self.tesseract_ready: bool = False
        self.transcription_in_progress: bool = False


class OcrController(QObject):
    """Conecta los botones de la vista con las acciones de carga y transcripción."""

    def __init__(self, view: OcrView) -> None:
        """Registra los callbacks de la vista y crea el estado en memoria."""
        super().__init__()
        self.view = view
        self.state = AppState()
        self._preview_source: Image.Image | None = None

        self._preview_resize_timer = QTimer(self)
        self._preview_resize_timer.setSingleShot(True)
        self._preview_resize_timer.timeout.connect(self._render_preview)

        self.view.open_button.clicked.connect(self.on_open_image)
        self.view.transcribe_button.clicked.connect(self.on_transcribe)
        self.view.preview_label.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Reprograma el reescalado de la vista previa ante el resize de `preview_label`."""
        if watched is self.view.preview_label and event.type() == QEvent.Resize:
            self._preview_resize_timer.start(PREVIEW_RESIZE_DEBOUNCE_MS)
        return super().eventFilter(watched, event)

    def on_open_image(self) -> None:
        """Abre un diálogo de selección de archivo, carga la imagen y actualiza la vista previa."""
        path, _ = QFileDialog.getOpenFileName(self.view, "Abrir imagen")
        if not path:
            return

        try:
            image = Image.open(path)
            image.load()
        except Exception as error:
            QMessageBox.critical(self.view, "Error al cargar la imagen", str(error))
            return

        self._preview_source = image
        self._render_preview()
        self.state.image_path = path
        self.view.enable_transcribe_button()

    def _render_preview(self) -> None:
        """Reescala la imagen fuente al tamaño actual del recuadro de vista previa."""
        if self._preview_source is None:
            return

        label = self.view.preview_label
        width, height = label.width(), label.height()
        if width <= 1 or height <= 1:
            return

        fitted = ImageOps.contain(self._preview_source, (width, height))
        pixmap = QPixmap.fromImage(ImageQt(fitted.convert("RGBA")))
        self.view.set_preview_image(pixmap)

    def on_transcribe(self) -> None:
        """Transcribe la imagen cargada usando el idioma seleccionado en la vista."""
        if self.state.transcription_in_progress:
            return

        self.state.selected_language = self.view.get_selected_language()
        language_code = LANGUAGE_MAP[self.state.selected_language]
        tesseract_path = resolve_tesseract_path()

        if tesseract_path is None:
            tesseract_path = self._prompt_tesseract_path()
            if tesseract_path is None:
                return

        self._start_transcription(language_code, tesseract_path)

    def _start_transcription(self, language_code: str, tesseract_path: str | None) -> None:
        """Lanza la transcripción en un `QThread` y arranca el contador de segundos en vivo."""
        self.state.transcription_in_progress = True
        self.view.disable_transcribe_button()
        self._transcription_start = time.monotonic()

        self._worker = TranscriptionWorker(self.state.image_path, language_code, tesseract_path, self)
        self._worker.succeeded.connect(self._on_transcription_succeeded)
        self._worker.failed.connect(self._on_transcription_failed)
        self._worker.start()

        self._counter_timer = QTimer(self)
        self._counter_timer.timeout.connect(self._update_counter)
        self._counter_timer.start(COUNTER_INTERVAL_MS)
        self._update_counter()

    def _update_counter(self) -> None:
        """Actualiza el contador de segundos mientras la transcripción está en curso."""
        elapsed = int(time.monotonic() - self._transcription_start)
        self.view.set_result_text(f"Procesando... {elapsed}s")

    def _on_transcription_succeeded(self, result: str) -> None:
        """Muestra el resultado de la transcripción al terminar con éxito."""
        self._counter_timer.stop()
        self.view.set_result_text(result)
        self._finish_transcription()

    def _on_transcription_failed(self, error_message: str) -> None:
        """Muestra el error de la transcripción al terminar con una excepción."""
        self._counter_timer.stop()
        QMessageBox.critical(self.view, "Error al transcribir", error_message)
        self._finish_transcription()

    def _finish_transcription(self) -> None:
        """Reactiva el botón "Transcribir" y limpia el estado de "en progreso"."""
        self.state.transcription_in_progress = False
        self.view.enable_transcribe_button()

    def _prompt_tesseract_path(self) -> str | None:
        """Pide al usuario la ruta del ejecutable de Tesseract y la persiste si es válida."""
        path, _ = QFileDialog.getOpenFileName(
            self.view,
            "Ubicar tesseract.exe",
            filter="Ejecutables (*.exe)",
        )
        if not path or not os.path.exists(path):
            return None

        save_tesseract_path(path)
        return path
