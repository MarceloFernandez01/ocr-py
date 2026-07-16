"""Conecta los eventos de la vista con la lógica del Model."""

import time

from PIL import Image, ImageOps
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QEvent, QObject, QPointF, QRect, QRectF, QThread, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox

from controller.common import COUNTER_INTERVAL_MS, LANGUAGE_MAP, processing_label, prompt_tesseract_path
from model.ocr_model import transcribe_cropped_image, transcribe_large_image
from model.tesseract_locator import resolve_tesseract_path
from view.ocr_view import OcrView

PREVIEW_RESIZE_DEBOUNCE_MS = 120
CROP_MIN_SIZE = 10


class TranscriptionWorker(QThread):
    """Corre la transcripción en un hilo aparte y emite el resultado por señal."""

    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        image_path: str,
        language_code: str,
        tesseract_path: str | None,
        cropped_image: Image.Image | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Guarda los parámetros de la transcripción a ejecutar en `run()`.

        Si `cropped_image` no es None, `run()` transcribe esa región recortada
        en vez de la imagen completa en `image_path`.
        """
        super().__init__(parent)
        self.image_path = image_path
        self.language_code = language_code
        self.tesseract_path = tesseract_path
        self.cropped_image = cropped_image

    def run(self) -> None:
        """Ejecuta la transcripción y emite `succeeded` o `failed` según el resultado."""
        try:
            if self.cropped_image is not None:
                result = transcribe_cropped_image(self.cropped_image, self.language_code, self.tesseract_path)
            else:
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
        self.transcription_in_progress: bool = False


class OcrController(QObject):
    """Conecta los botones de la vista con las acciones de carga y transcripción."""

    def __init__(self, view: OcrView) -> None:
        """Registra los callbacks de la vista y crea el estado en memoria."""
        super().__init__()
        self.view = view
        self.state = AppState()
        self._preview_source: Image.Image | None = None
        self._preview_image_rect = QRectF()
        self._crop_box: tuple[int, int, int, int] | None = None
        self._crop_mode_active = False
        self._crop_drag_start: QPointF | None = None

        self._preview_resize_timer = QTimer(self)
        self._preview_resize_timer.setSingleShot(True)
        self._preview_resize_timer.timeout.connect(self._render_preview)

        self.view.open_button.clicked.connect(self.on_open_image)
        self.view.transcribe_button.clicked.connect(self.on_transcribe)
        self.view.crop_toggled.connect(self.on_crop_toggled)
        self.view.preview_label.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Reprograma el reescalado de la vista previa y maneja el arrastre de recorte."""
        if watched is self.view.preview_label:
            if event.type() == QEvent.Resize:
                self._preview_resize_timer.start(PREVIEW_RESIZE_DEBOUNCE_MS)
            elif event.type() == QEvent.MouseButtonPress and (
                self._crop_mode_active or self._crop_box is not None
            ):
                self._on_crop_mouse_press(event)
                return True
            elif event.type() == QEvent.MouseMove and self._crop_drag_start is not None:
                self._on_crop_mouse_move(event)
                return True
            elif event.type() == QEvent.MouseButtonRelease and self._crop_drag_start is not None:
                self._on_crop_mouse_release(event)
                return True
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

        self._crop_box = None
        self._crop_mode_active = False
        self.view.hide_crop_rect()
        self.view.update_crop_button(has_crop=False, armed=False)

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

        fitted_width, fitted_height = fitted.size
        offset_x = (width - fitted_width) / 2
        offset_y = (height - fitted_height) / 2
        self._preview_image_rect = QRectF(offset_x, offset_y, fitted_width, fitted_height)

        if self._crop_box is not None:
            self._redraw_crop_rect()

    def on_crop_toggled(self) -> None:
        """Maneja el click en el botón único de recorte.

        Si ya hay una región seleccionada, la limpia (equivalente a "Quitar
        recorte"). Si no hay región, alterna el modo armado que espera el
        próximo arrastre sobre la vista previa (equivalente a "Activar
        recorte", con un segundo click para cancelar el armado).
        """
        if self._crop_box is not None:
            self._crop_box = None
            self._crop_mode_active = False
            self.view.hide_crop_rect()
            self.view.update_crop_button(has_crop=False, armed=False)
            return

        self._crop_mode_active = not self._crop_mode_active
        self.view.update_crop_button(has_crop=False, armed=self._crop_mode_active)

    def _clamp_to_image_rect(self, point: QPointF) -> QPointF:
        """Restringe `point` (coords de `preview_label`) al área visible de la imagen."""
        rect = self._preview_image_rect
        x = max(rect.left(), min(rect.right(), point.x()))
        y = max(rect.top(), min(rect.bottom(), point.y()))
        return QPointF(x, y)

    def _map_point_to_original(self, point: QPointF) -> tuple[float, float]:
        """Mapea un punto en coords de `preview_label` a coords de la imagen original."""
        rect = self._preview_image_rect
        original_width, original_height = self._preview_source.size
        scale_x = original_width / rect.width() if rect.width() else 1.0
        scale_y = original_height / rect.height() if rect.height() else 1.0
        x = max(0.0, min(original_width, (point.x() - rect.x()) * scale_x))
        y = max(0.0, min(original_height, (point.y() - rect.y()) * scale_y))
        return x, y

    def _redraw_crop_rect(self) -> None:
        """Reposiciona el rectángulo de recorte persistente según el render actual de la preview."""
        rect = self._preview_image_rect
        original_width, original_height = self._preview_source.size
        scale_x = rect.width() / original_width if original_width else 1.0
        scale_y = rect.height() / original_height if original_height else 1.0
        left, top, right, bottom = self._crop_box

        preview_rect = QRect(
            round(rect.x() + left * scale_x),
            round(rect.y() + top * scale_y),
            round((right - left) * scale_x),
            round((bottom - top) * scale_y),
        )
        self.view.show_crop_rect(preview_rect)

    def _on_crop_mouse_press(self, event) -> None:
        """Guarda el punto inicial del arrastre y muestra el rectángulo naciente."""
        point = self._clamp_to_image_rect(event.position())
        self._crop_drag_start = point
        self.view.show_crop_rect(QRect(point.toPoint(), point.toPoint()))

    def _on_crop_mouse_move(self, event) -> None:
        """Redimensiona el rectángulo de selección en tiempo real durante el arrastre."""
        point = self._clamp_to_image_rect(event.position())
        rect = QRect(self._crop_drag_start.toPoint(), point.toPoint()).normalized()
        self.view.show_crop_rect(rect)

    def _on_crop_mouse_release(self, event) -> None:
        """Confirma o descarta el recorte según el umbral mínimo al soltar el mouse."""
        point = self._clamp_to_image_rect(event.position())
        rect = QRect(self._crop_drag_start.toPoint(), point.toPoint()).normalized()
        self._crop_drag_start = None

        if rect.width() < CROP_MIN_SIZE or rect.height() < CROP_MIN_SIZE:
            if self._crop_box is not None:
                self._redraw_crop_rect()
            else:
                self._crop_mode_active = False
                self.view.hide_crop_rect()
                self.view.update_crop_button(has_crop=False, armed=False)
            return

        start_x, start_y = self._map_point_to_original(QPointF(rect.left(), rect.top()))
        end_x, end_y = self._map_point_to_original(QPointF(rect.right(), rect.bottom()))
        self._crop_box = (
            round(min(start_x, end_x)),
            round(min(start_y, end_y)),
            round(max(start_x, end_x)),
            round(max(start_y, end_y)),
        )
        self._crop_mode_active = False
        self._redraw_crop_rect()
        self.view.update_crop_button(has_crop=True, armed=False)

    def on_transcribe(self) -> None:
        """Transcribe la imagen cargada usando el idioma seleccionado en la vista."""
        if self.state.transcription_in_progress:
            return

        self.state.selected_language = self.view.get_selected_language()
        language_code = LANGUAGE_MAP[self.state.selected_language]
        tesseract_path = resolve_tesseract_path()

        if tesseract_path is None:
            tesseract_path = prompt_tesseract_path(self.view)
            if tesseract_path is None:
                return

        self._start_transcription(language_code, tesseract_path)

    def _start_transcription(self, language_code: str, tesseract_path: str | None) -> None:
        """Lanza la transcripción en un `QThread` y arranca el contador de segundos en vivo."""
        self.state.transcription_in_progress = True
        self.view.disable_transcribe_button()
        self._transcription_start = time.monotonic()

        cropped_image = None
        if self._crop_box is not None and self._preview_source is not None:
            cropped_image = self._preview_source.crop(self._crop_box)

        self._worker = TranscriptionWorker(
            self.state.image_path, language_code, tesseract_path, cropped_image=cropped_image, parent=self
        )
        self._worker.succeeded.connect(self._on_transcription_succeeded)
        self._worker.failed.connect(self._on_transcription_failed)
        self._worker.start()

        self._counter_timer = QTimer(self)
        self._counter_timer.timeout.connect(self._update_counter)
        self._counter_timer.start(COUNTER_INTERVAL_MS)
        self._update_counter()

    def _update_counter(self) -> None:
        """Actualiza el contador de segundos mientras la transcripción está en curso."""
        self.view.set_result_text(processing_label(self._transcription_start))

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
