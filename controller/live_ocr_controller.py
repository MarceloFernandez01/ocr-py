"""Conecta los eventos de OCR en vivo con el ciclo de captura, diff y transcripción."""

import os
import time

import numpy as np
from PIL import Image
from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox

from model.config_model import save_tesseract_path
from model.image_diff import has_changed
from model.ocr_model import transcribe_image_variants
from model.tesseract_locator import resolve_tesseract_path
from view.live_ocr_view import LiveOcrView
from view.screen_overlay import ScreenOverlay

POLL_INTERVAL_MS = 1500
COUNTER_INTERVAL_MS = 200

LANGUAGE_MAP = {
    "Español": "spa",
    "Inglés": "eng",
    "Ambos": "spa+eng",
}


class LiveTranscriptionWorker(QThread):
    """Corre `transcribe_image_variants` en un hilo aparte y emite el resultado por señal."""

    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, image: Image.Image, language_code: str, tesseract_path: str | None, parent: QObject | None = None) -> None:
        """Guarda los parámetros de la transcripción a ejecutar en `run()`."""
        super().__init__(parent)
        self.image = image
        self.language_code = language_code
        self.tesseract_path = tesseract_path

    def run(self) -> None:
        """Ejecuta la transcripción y emite `succeeded` o `failed` según el resultado."""
        try:
            result = transcribe_image_variants(self.image, self.language_code, self.tesseract_path)
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.succeeded.emit(result)


class LiveOcrController(QObject):
    """Orquesta el ciclo completo de OCR en vivo: crea/destruye `ScreenOverlay`, corre el
    `QTimer` de polling (oculta overlay -> `QScreen.grabWindow` -> muestra overlay ->
    diff vía `model/image_diff.py` -> si cambió, dispara transcripción async con
    `QThread`), y actualiza `LiveOcrView` con cada captura/resultado. Expone
    `start()`/`stop()` para que `MainWindow` los invoque al navegar entre vistas.
    """

    def __init__(self, view: LiveOcrView) -> None:
        """Registra la vista y conecta el botón "Activar selección" a `start()`."""
        super().__init__()
        self.view = view
        self._overlay: ScreenOverlay | None = None
        self._timer: QTimer | None = None
        self._previous_capture: Image.Image | None = None
        self._worker: LiveTranscriptionWorker | None = None
        self._tesseract_path: str | None = None
        self._transcription_start: float = 0.0

        self._counter_timer = QTimer(self)
        self._counter_timer.timeout.connect(self._update_counter)

        self.view.activate_selection_clicked.connect(self.start)

    def start(self) -> None:
        """Crea el overlay y arranca el polling. No-op si ya hay un overlay activo."""
        if self._overlay is not None:
            return

        tesseract_path = resolve_tesseract_path()
        if tesseract_path is None:
            tesseract_path = self._prompt_tesseract_path()
            if tesseract_path is None:
                return

        self._tesseract_path = tesseract_path
        self._previous_capture = None

        self._overlay = ScreenOverlay()
        self._overlay.closed.connect(self._on_overlay_closed)
        self._overlay.geometry_changed.connect(self._poll)
        self._overlay.show()
        self.view.disable_activate_button()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(POLL_INTERVAL_MS)
        self._poll()

    def stop(self) -> None:
        """Detiene el polling y cierra/destruye el overlay si estaba activo."""
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

        self._counter_timer.stop()

        if self._worker is not None:
            self._worker.succeeded.disconnect(self._on_transcription_succeeded)
            self._worker.failed.disconnect(self._on_transcription_failed)
            self._worker.finished.connect(self._worker.deleteLater)
            self._worker = None

        if self._overlay is not None:
            self._overlay.closed.disconnect(self._on_overlay_closed)
            self._overlay.geometry_changed.disconnect(self._poll)
            self._overlay.close()
            self._overlay = None

        self._previous_capture = None
        self.view.enable_activate_button()

    def _on_overlay_closed(self) -> None:
        """Detiene el polling al cerrar el overlay con la X, sin tocar el resto del estado."""
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self._counter_timer.stop()
        self._overlay = None
        self._previous_capture = None
        self.view.enable_activate_button()

    def _poll(self) -> None:
        """Captura el área del overlay, actualiza la miniatura y dispara transcripción si cambió."""
        if self._overlay is None:
            return

        capture_rect = self._overlay.capture_geometry()
        screen = self._overlay.screen()

        self._overlay.hide()
        screen_geometry = screen.geometry()
        pixmap = screen.grabWindow(
            0,
            capture_rect.x() - screen_geometry.x(),
            capture_rect.y() - screen_geometry.y(),
            capture_rect.width(),
            capture_rect.height(),
        )
        self._overlay.show()

        self._update_thumbnail(pixmap)

        current = self._pixmap_to_pil(pixmap)
        if not has_changed(self._previous_capture, current):
            return

        self._previous_capture = current
        self._start_transcription(current)

    def _update_thumbnail(self, pixmap: QPixmap) -> None:
        """Reescala `pixmap` al tamaño del recuadro de miniatura y lo muestra en la vista."""
        label = self.view.preview_label
        scaled = pixmap.scaled(label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.view.set_preview_image(scaled)

    def _start_transcription(self, image: Image.Image) -> None:
        """Lanza la transcripción de `image` en un `QThread`, reemplazando el worker vigente."""
        language_code = LANGUAGE_MAP[self.view.get_selected_language()]

        self._transcription_start = time.monotonic()
        self._update_counter()
        worker = LiveTranscriptionWorker(image, language_code, self._tesseract_path, self)
        self._worker = worker
        worker.succeeded.connect(self._on_transcription_succeeded)
        worker.failed.connect(self._on_transcription_failed)
        worker.start()
        self._counter_timer.start(COUNTER_INTERVAL_MS)

    def _update_counter(self) -> None:
        """Actualiza el contador de segundos mientras la transcripción está en curso."""
        elapsed = int(time.monotonic() - self._transcription_start)
        self.view.set_result_text(f"Procesando... {elapsed}s")

    def _on_transcription_succeeded(self, text: str) -> None:
        """Muestra el resultado si proviene del worker vigente; descarta resultados obsoletos."""
        if self.sender() is not self._worker:
            return
        self._counter_timer.stop()
        self._worker = None
        self.view.set_result_text(text)

    def _on_transcription_failed(self, error_message: str) -> None:
        """Muestra el error si proviene del worker vigente; descarta fallos obsoletos."""
        if self.sender() is not self._worker:
            return
        self._counter_timer.stop()
        self._worker = None
        QMessageBox.critical(self.view, "Error al transcribir", error_message)

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

    @staticmethod
    def _pixmap_to_pil(pixmap: QPixmap) -> Image.Image:
        """Convierte un `QPixmap` (capturado con `grabWindow`) a `PIL.Image` en modo RGB."""
        qimage = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
        width, height = qimage.width(), qimage.height()
        buffer = qimage.constBits()
        array = np.frombuffer(buffer, dtype=np.uint8).reshape(height, width, 4)
        return Image.fromarray(array, "RGBA").convert("RGB")
