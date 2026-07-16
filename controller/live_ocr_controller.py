"""Conecta los eventos de OCR en vivo con el ciclo de captura, diff y transcripción."""

import time

import numpy as np
from PIL import Image
from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QMessageBox

from controller.common import COUNTER_INTERVAL_MS, LANGUAGE_MAP, processing_label, prompt_tesseract_path
from model.image_diff import has_changed
from model.ocr_model import transcribe_image_variants
from model.tesseract_locator import resolve_tesseract_path
from model.translation_model import translate_text
from view.live_ocr_view import LiveOcrView
from view.screen_overlay import ScreenOverlay

POLL_INTERVAL_MS = 1500


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


class TranslationWorker(QThread):
    """Corre `translate_text` en un hilo aparte. Mismo patrón que
    `LiveTranscriptionWorker`: `run()` llama al model y emite `translated(str)`
    con el resultado o `error(str)` si `translate_text` levanta una excepción
    (ej. sin internet en la primera descarga del modelo).
    """

    translated = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        parent: QObject | None = None,
    ) -> None:
        """Guarda los parámetros de la traducción a ejecutar en `run()`."""
        super().__init__(parent)
        self.text = text
        self.source_lang = source_lang
        self.target_lang = target_lang

    def run(self) -> None:
        """Ejecuta la traducción y emite `finished` o `error` según el resultado."""
        try:
            result = translate_text(self.text, self.source_lang, self.target_lang)
        except Exception as error:
            self.error.emit(str(error))
        else:
            self.translated.emit(result)


class LiveOcrController(QObject):
    """Orquesta el ciclo completo de OCR en vivo: crea/destruye `ScreenOverlay` vía
    `activate_selection()`, arranca/detiene el `QTimer` de polling vía
    `toggle_transcription()` (`QScreen.grabWindow` sobre `capture_geometry()`, que ya
    excluye el borde y la barra de controles del overlay -> diff vía
    `model/image_diff.py` -> si cambió, dispara transcripción async con `QThread`),
    y actualiza `LiveOcrView` con cada captura/resultado.
    Expone `stop()` para que `MainWindow` lo invoque al navegar afuera de la vista.
    """

    def __init__(self, view: LiveOcrView) -> None:
        """Registra la vista y conecta "Activar selección"/"Iniciar transcripción" a sus handlers."""
        super().__init__()
        self.view = view
        self._overlay: ScreenOverlay | None = None
        self._timer: QTimer | None = None
        self._previous_capture: Image.Image | None = None
        self._worker: LiveTranscriptionWorker | None = None
        self._tesseract_path: str | None = None
        self._transcription_start: float = 0.0
        self._translation_active: bool = False
        self._translation_worker: TranslationWorker | None = None
        self._last_transcribed_text: str | None = None
        self._interacting: bool = False

        self._counter_timer = QTimer(self)
        self._counter_timer.timeout.connect(self._update_counter)

        self.view.activate_selection_clicked.connect(self.activate_selection)
        self.view.toggle_transcription_clicked.connect(self.toggle_transcription)
        self.view.translate_toggled.connect(self.on_translate_toggled)

    def activate_selection(self) -> None:
        """Crea (o recrea) el overlay en posición/tamaño default. No arranca el polling."""
        if self._overlay is not None:
            if self._timer is not None:
                self._timer.stop()
                self._timer = None
            self._counter_timer.stop()
            self._disconnect_overlay_signals()
            self._overlay.close()
            self._overlay = None

        self._previous_capture = None
        self._interacting = False

        self._overlay = ScreenOverlay()
        self._overlay.closed.connect(self._on_overlay_closed)
        self._overlay.geometry_changed.connect(self._on_interaction_finished)
        self._overlay.interaction_started.connect(self._on_interaction_started)
        self._overlay.toggle_transcription_requested.connect(self.toggle_transcription)
        self._overlay.show()

        self.view.enable_transcription_button()
        self.view.set_transcription_button_running(False)
        self._overlay.set_toggle_enabled(True)
        self._overlay.set_running(False)

    def _disconnect_overlay_signals(self) -> None:
        """Desconecta las señales del overlay vigente antes de cerrarlo/descartarlo."""
        self._overlay.closed.disconnect(self._on_overlay_closed)
        self._overlay.geometry_changed.disconnect(self._on_interaction_finished)
        self._overlay.interaction_started.disconnect(self._on_interaction_started)
        self._overlay.toggle_transcription_requested.disconnect(self.toggle_transcription)

    def toggle_transcription(self) -> None:
        """Arranca o detiene el polling de transcripción según el estado actual del `QTimer`."""
        if self._timer is None:
            tesseract_path = resolve_tesseract_path()
            if tesseract_path is None:
                tesseract_path = prompt_tesseract_path(self.view)
                if tesseract_path is None:
                    return

            self._tesseract_path = tesseract_path

            self._timer = QTimer(self)
            self._timer.timeout.connect(self._poll)
            self._timer.start(POLL_INTERVAL_MS)
            self._poll()
            self.view.set_transcription_button_running(True)
            if self._overlay is not None:
                self._overlay.set_running(True)
        else:
            self._timer.stop()
            self._timer = None
            self.view.set_transcription_button_running(False)
            if self._overlay is not None:
                self._overlay.set_running(False)

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

        self._cancel_translation_worker()

        if self._overlay is not None:
            self._disconnect_overlay_signals()
            self._overlay.close()
            self._overlay = None

        self._previous_capture = None
        self._interacting = False
        self.view.enable_activate_button()
        self.view.disable_transcription_button()
        self.view.set_transcription_button_running(False)

    def _on_overlay_closed(self) -> None:
        """Detiene el polling al cerrar el overlay con la X, sin tocar el resto del estado."""
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self._counter_timer.stop()
        self._cancel_translation_worker()
        self._overlay = None
        self._previous_capture = None
        self._interacting = False
        self.view.enable_activate_button()
        self.view.disable_transcription_button()
        self.view.set_transcription_button_running(False)

    def _on_interaction_started(self) -> None:
        """Pausa la captura mientras se arrastra/redimensiona la región, sin detener el `QTimer`."""
        self._interacting = True
        self._counter_timer.stop()
        self._worker = None

    def _on_interaction_finished(self) -> None:
        """Reanuda la captura al soltar la región, recapturando de inmediato si el polling corre."""
        self._interacting = False
        if self._timer is not None:
            self._poll()

    def _cancel_translation_worker(self) -> None:
        """Descarta cualquier `TranslationWorker` en curso sin limpiar el texto ya mostrado."""
        if self._translation_worker is None:
            return

        self._translation_worker.translated.disconnect(self._on_translation_finished)
        self._translation_worker.error.disconnect(self._on_translation_error)
        self._translation_worker.finished.connect(self._translation_worker.deleteLater)
        self._translation_worker = None

    def _poll(self) -> None:
        """Captura el área del overlay, actualiza la miniatura y dispara transcripción si cambió."""
        if self._overlay is None or self._timer is None or self._interacting:
            return

        capture_rect = self._overlay.capture_geometry()
        screen = self._overlay.screen()

        screen_geometry = screen.geometry()
        pixmap = screen.grabWindow(
            0,
            capture_rect.x() - screen_geometry.x(),
            capture_rect.y() - screen_geometry.y(),
            capture_rect.width(),
            capture_rect.height(),
        )

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
        self.view.set_result_text(processing_label(self._transcription_start))

    def _on_transcription_succeeded(self, text: str) -> None:
        """Muestra el resultado si proviene del worker vigente; descarta resultados obsoletos."""
        if self.sender() is not self._worker:
            return
        self._counter_timer.stop()
        self._worker = None
        self.view.set_result_text(text)
        self._last_transcribed_text = text
        if self._translation_active:
            self._start_translation(text)

    def _on_transcription_failed(self, error_message: str) -> None:
        """Muestra el error si proviene del worker vigente; descarta fallos obsoletos."""
        if self.sender() is not self._worker:
            return
        self._counter_timer.stop()
        self._worker = None
        QMessageBox.critical(self.view, "Error al transcribir", error_message)

    def on_translate_toggled(self) -> None:
        """Alterna `_translation_active`; al activar, traduce el texto ya reconocido si existe."""
        self._translation_active = not self._translation_active
        self.view.set_translation_button_active(self._translation_active)
        if self._translation_active and self._last_transcribed_text:
            self._start_translation(self._last_transcribed_text)

    def _start_translation(self, text: str) -> None:
        """Lanza la traducción de `text` en un `QThread`, reemplazando el worker vigente."""
        source_lang = LANGUAGE_MAP[self.view.get_source_language()]
        target_lang = LANGUAGE_MAP[self.view.get_target_language()]

        self.view.set_translated_text("Traduciendo...")
        worker = TranslationWorker(text, source_lang, target_lang, self)
        self._translation_worker = worker
        worker.translated.connect(self._on_translation_finished)
        worker.error.connect(self._on_translation_error)
        worker.start()

    def _on_translation_finished(self, translated_text: str) -> None:
        """Muestra la traducción si proviene del worker vigente; descarta resultados obsoletos."""
        if self.sender() is not self._translation_worker:
            return
        self._translation_worker = None
        self.view.set_translated_text(translated_text)

    def _on_translation_error(self, error_message: str) -> None:
        """Muestra el error si proviene del worker vigente; el polling sigue sin interrupciones."""
        if self.sender() is not self._translation_worker:
            return
        self._translation_worker = None
        QMessageBox.critical(self.view, "Error al traducir", error_message)

    @staticmethod
    def _pixmap_to_pil(pixmap: QPixmap) -> Image.Image:
        """Convierte un `QPixmap` (capturado con `grabWindow`) a `PIL.Image` en modo RGB."""
        qimage = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
        width, height = qimage.width(), qimage.height()
        buffer = qimage.constBits()
        array = np.frombuffer(buffer, dtype=np.uint8).reshape(height, width, 4)
        return Image.fromarray(array, "RGBA").convert("RGB")
