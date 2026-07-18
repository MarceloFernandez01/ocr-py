"""Conecta los eventos de la vista con la lógica del Model."""

import time

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, QEvent, QObject, QPointF, QRect, QRectF, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox

from controller.common import COUNTER_INTERVAL_MS, LANGUAGE_MAP, processing_label, prompt_tesseract_path
from model.ocr_model import transcribe_cropped_image, transcribe_large_image
from model.tesseract_locator import resolve_tesseract_path
from view.ocr_view import OcrView

PREVIEW_RESIZE_DEBOUNCE_MS = 120
CROP_MIN_SIZE = 10

ZOOM_MIN = 1.0
ZOOM_MAX = 5.0
ZOOM_STEP = 1.25
"""Factor de zoom relativo a la imagen ajustada a `preview_label` (1.0 = fit
actual, igual que el comportamiento previo a esta spec). Cada notch de rueda
multiplica o divide `_zoom` por `ZOOM_STEP`, clampeado a [ZOOM_MIN, ZOOM_MAX]."""


def _fit_within_box(source_size: tuple[int, int], box_size: tuple[int, int]) -> tuple[int, int]:
    """Calcula el tamaño resultante de ajustar `source_size` dentro de `box_size` preservando la relación de aspecto."""
    source_width, source_height = source_size
    box_width, box_height = box_size
    source_ratio = source_width / source_height
    box_ratio = box_width / box_height
    if source_ratio > box_ratio:
        return box_width, max(1, round(source_height / source_width * box_width))
    return max(1, round(source_width / source_height * box_height)), box_height


class TranscriptionSignals(QObject):
    """Señales emitidas por `TranscriptionRunnable` al terminar (los `QRunnable` no tienen señales propias)."""

    succeeded = Signal(str)
    failed = Signal(str)


class TranscriptionRunnable(QRunnable):
    """Corre la transcripción en un hilo del `QThreadPool` y emite el resultado por `TranscriptionSignals`."""

    def __init__(
        self,
        image_path: str,
        language_code: str,
        tesseract_path: str | None,
        signals: TranscriptionSignals,
        cropped_image: Image.Image | None = None,
    ) -> None:
        """Guarda los parámetros de la transcripción a ejecutar en `run()`.

        Si `cropped_image` no es None, `run()` transcribe esa región recortada
        en vez de la imagen completa en `image_path`.
        """
        super().__init__()
        self.image_path = image_path
        self.language_code = language_code
        self.tesseract_path = tesseract_path
        self.cropped_image = cropped_image
        self.signals = signals

    def run(self) -> None:
        """Ejecuta la transcripción y emite `succeeded` o `failed` según el resultado."""
        try:
            if self.cropped_image is not None:
                result = transcribe_cropped_image(self.cropped_image, self.language_code, self.tesseract_path)
            else:
                result = transcribe_large_image(self.image_path, self.language_code, self.tesseract_path)
        except Exception as error:
            self.signals.failed.emit(str(error))
        else:
            self.signals.succeeded.emit(result)


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
        self._crop_drag_start: QPointF | None = None

        self._zoom: float = 1.0
        self._zoom_center: tuple[float, float] | None = None
        self._pan_drag_start: QPointF | None = None
        self._pan_start_center: tuple[float, float] | None = None

        self._worker_signals = TranscriptionSignals(self)
        self._worker_signals.succeeded.connect(self._on_transcription_succeeded)
        self._worker_signals.failed.connect(self._on_transcription_failed)

        self._preview_resize_timer = QTimer(self)
        self._preview_resize_timer.setSingleShot(True)
        self._preview_resize_timer.timeout.connect(self._render_preview)

        self.view.open_button.clicked.connect(self.on_open_image)
        self.view.transcribe_button.clicked.connect(self.on_transcribe)
        self.view.crop_toggled.connect(self.on_crop_toggled)
        self.view.reset_zoom_button.clicked.connect(self.on_reset_zoom)
        self.view.preview_label.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Reprograma el reescalado de la vista previa y maneja zoom, paneo y arrastre de recorte."""
        if watched is self.view.preview_label:
            if event.type() == QEvent.Resize:
                self._preview_resize_timer.start(PREVIEW_RESIZE_DEBOUNCE_MS)
            elif event.type() == QEvent.Wheel:
                self._on_wheel_zoom(event)
                return True
            elif event.type() == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
                self._on_pan_mouse_press(event)
                return True
            elif event.type() == QEvent.MouseButtonPress:
                self._on_crop_mouse_press(event)
                return True
            elif event.type() == QEvent.MouseMove and self._pan_drag_start is not None:
                self._on_pan_mouse_move(event)
                return True
            elif event.type() == QEvent.MouseMove and self._crop_drag_start is not None:
                self._on_crop_mouse_move(event)
                return True
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.RightButton:
                self._on_pan_mouse_release(event)
                return True
            elif event.type() == QEvent.MouseButtonRelease and self._crop_drag_start is not None:
                self._on_crop_mouse_release(event)
                return True
        return super().eventFilter(watched, event)

    def _on_wheel_zoom(self, event) -> None:
        """Aplica un paso de zoom centrado en el punto de la imagen original bajo el cursor."""
        if self._preview_source is None:
            return

        point = event.position()
        if not self._preview_image_rect.contains(point):
            return

        anchor_x, anchor_y = self._map_point_to_original(point)

        if event.angleDelta().y() > 0:
            new_zoom = self._zoom * ZOOM_STEP
        else:
            new_zoom = self._zoom / ZOOM_STEP
        self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, new_zoom))

        original_width, original_height = self._preview_source.size
        new_region_width = original_width / self._zoom
        new_region_height = original_height / self._zoom

        rect = self._preview_image_rect
        fraction_x = (point.x() - rect.x()) / rect.width() if rect.width() else 0.5
        fraction_y = (point.y() - rect.y()) / rect.height() if rect.height() else 0.5

        new_region_left = anchor_x - fraction_x * new_region_width
        new_region_top = anchor_y - fraction_y * new_region_height

        self._zoom_center = (
            new_region_left + new_region_width / 2,
            new_region_top + new_region_height / 2,
        )
        self._render_preview()

    def _on_pan_mouse_press(self, event) -> None:
        """Guarda el punto inicial del arrastre de paneo con click derecho."""
        if self._preview_source is None:
            return
        self._pan_drag_start = event.position()
        self._pan_start_center = self._zoom_center

    def _on_pan_mouse_move(self, event) -> None:
        """Desplaza `self._zoom_center` según el arrastre acumulado desde el inicio del paneo."""
        delta = event.position() - self._pan_drag_start
        rect = self._preview_image_rect
        left, top, right, bottom = self._current_visible_region()
        region_width = right - left
        region_height = bottom - top
        scale_x = region_width / rect.width() if rect.width() else 1.0
        scale_y = region_height / rect.height() if rect.height() else 1.0

        start_x, start_y = self._pan_start_center
        self._zoom_center = (
            start_x - delta.x() * scale_x,
            start_y - delta.y() * scale_y,
        )
        self._render_preview()

    def _on_pan_mouse_release(self, event) -> None:
        """Finaliza el arrastre de paneo con click derecho."""
        self._pan_drag_start = None
        self._pan_start_center = None

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
        self.view.hide_crop_rect()
        self.view.update_crop_button(has_crop=False)

        self._preview_source = image
        self._zoom = 1.0
        self._zoom_center = (image.width / 2, image.height / 2)
        self._render_preview()
        self.state.image_path = path
        self.view.enable_transcribe_button()

    def _current_visible_region(self) -> tuple[float, float, float, float]:
        """Calcula (left, top, right, bottom) en coordenadas de la imagen original
        que representan la región actualmente visible en `preview_label`, según
        `self._zoom` y `self._zoom_center`. El tamaño de la región es
        (original_width / zoom, original_height / zoom); el centro se clampea
        para que la región completa quede dentro de los límites de la imagen
        (mismo mecanismo que ya clampea el recorte, aplicado acá a la cámara)."""
        original_width, original_height = self._preview_source.size
        region_width = original_width / self._zoom
        region_height = original_height / self._zoom

        center_x, center_y = self._zoom_center
        half_width = region_width / 2
        half_height = region_height / 2

        center_x = max(half_width, min(original_width - half_width, center_x))
        center_y = max(half_height, min(original_height - half_height, center_y))

        return (
            center_x - half_width,
            center_y - half_height,
            center_x + half_width,
            center_y + half_height,
        )

    def _render_preview(self) -> None:
        """Recorta la región visible (según zoom/paneo) y la reescala al recuadro fijo de vista previa."""
        if self._preview_source is None:
            return

        label = self.view.preview_label
        width, height = label.width(), label.height()
        if width <= 1 or height <= 1:
            return

        original_width, original_height = self._preview_source.size
        fitted_width, fitted_height = _fit_within_box((original_width, original_height), (width, height))
        offset_x = (width - fitted_width) / 2
        offset_y = (height - fitted_height) / 2
        self._preview_image_rect = QRectF(offset_x, offset_y, fitted_width, fitted_height)

        left, top, right, bottom = self._current_visible_region()
        region = self._preview_source.crop((round(left), round(top), round(right), round(bottom)))
        rendered = region.resize((fitted_width, fitted_height))
        pixmap = QPixmap.fromImage(ImageQt(rendered.convert("RGBA")))
        self.view.set_preview_image(pixmap)

        if self._crop_box is not None:
            self._redraw_crop_rect()

        self.view.position_zoom_label()
        if self._zoom != 1.0:
            self.view.set_zoom_label(f"{int(self._zoom * 100)}%")
        else:
            self.view.hide_zoom_label()

    def on_crop_toggled(self) -> None:
        """Maneja el click en "Quitar recorte": limpia la región seleccionada."""
        self._crop_box = None
        self.view.hide_crop_rect()
        self.view.update_crop_button(has_crop=False)

    def on_reset_zoom(self) -> None:
        """Restablece el zoom y el paneo al estado inicial (imagen completa ajustada)."""
        if self._preview_source is None:
            return
        self._zoom = 1.0
        self._zoom_center = (self._preview_source.width / 2, self._preview_source.height / 2)
        self._render_preview()

    def _clamp_to_image_rect(self, point: QPointF) -> QPointF:
        """Restringe `point` (coords de `preview_label`) al área visible de la imagen."""
        rect = self._preview_image_rect
        x = max(rect.left(), min(rect.right(), point.x()))
        y = max(rect.top(), min(rect.bottom(), point.y()))
        return QPointF(x, y)

    def _map_point_to_original(self, point: QPointF) -> tuple[float, float]:
        """Mapea un punto en coords de `preview_label` a coords de la imagen original, según la región visible actual."""
        rect = self._preview_image_rect
        region_left, region_top, region_right, region_bottom = self._current_visible_region()
        region_width = region_right - region_left
        region_height = region_bottom - region_top
        scale_x = region_width / rect.width() if rect.width() else 1.0
        scale_y = region_height / rect.height() if rect.height() else 1.0
        x = region_left + max(0.0, min(region_width, (point.x() - rect.x()) * scale_x))
        y = region_top + max(0.0, min(region_height, (point.y() - rect.y()) * scale_y))
        return x, y

    def _redraw_crop_rect(self) -> None:
        """Reposiciona el rectángulo de recorte persistente según la región visible actual."""
        rect = self._preview_image_rect
        region_left, region_top, region_right, region_bottom = self._current_visible_region()
        region_width = region_right - region_left
        region_height = region_bottom - region_top
        scale_x = rect.width() / region_width if region_width else 1.0
        scale_y = rect.height() / region_height if region_height else 1.0
        left, top, right, bottom = self._crop_box

        preview_rect = QRect(
            round(rect.x() + (left - region_left) * scale_x),
            round(rect.y() + (top - region_top) * scale_y),
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
                self.view.hide_crop_rect()
                self.view.update_crop_button(has_crop=False)
            return

        start_x, start_y = self._map_point_to_original(QPointF(rect.left(), rect.top()))
        end_x, end_y = self._map_point_to_original(QPointF(rect.right(), rect.bottom()))
        self._crop_box = (
            round(min(start_x, end_x)),
            round(min(start_y, end_y)),
            round(max(start_x, end_x)),
            round(max(start_y, end_y)),
        )
        self._redraw_crop_rect()
        self.view.update_crop_button(has_crop=True)

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
        """Lanza la transcripción en el `QThreadPool` global y arranca el contador de segundos en vivo."""
        self.state.transcription_in_progress = True
        self.view.disable_transcribe_button()
        self._transcription_start = time.monotonic()

        cropped_image = None
        if self._crop_box is not None and self._preview_source is not None:
            cropped_image = self._preview_source.crop(self._crop_box)

        runnable = TranscriptionRunnable(
            self.state.image_path, language_code, tesseract_path, self._worker_signals, cropped_image=cropped_image
        )
        QThreadPool.globalInstance().start(runnable)

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
