"""Conecta los eventos de OCR en vivo con el ciclo de captura, diff y transcripción."""

import time
from typing import TYPE_CHECKING

import keyring
import numpy as np
from PIL import Image
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QMessageBox

from controller.common import (
    COUNTER_INTERVAL_MS,
    LANGUAGE_MAP,
    format_claude_error,
    processing_label,
    prompt_tesseract_path,
)
from controller.global_hotkeys import HOTKEY_CLOSE_ID, HOTKEY_TOGGLE_ID, GlobalHotkeyManager
from model.claude_ocr_model import transcribe_image_claude
from model.claude_usage_model import register_call
from model.config_model import KEYRING_SERVICE, KEYRING_USERNAME, load_config
from model.image_diff import has_changed
from model.ocr_model import transcribe_image_variants
from model.tesseract_locator import resolve_tesseract_path
from model.text_diff import has_text_changed
from model.translation_model import translate_text
from view.live_ocr_view import LiveOcrView
from view.screen_overlay import ScreenOverlay

if TYPE_CHECKING:
    from view.main_window import MainWindow

POLL_INTERVAL_MS = 1500


class LiveTranscriptionSignals(QObject):
    """Señales emitidas por `LiveTranscriptionRunnable` al terminar (los `QRunnable` no tienen señales propias)."""

    succeeded = Signal(str)
    failed = Signal(str)


class LiveTranscriptionRunnable(QRunnable):
    """Corre `transcribe_image_variants` en un hilo del `QThreadPool` y emite el resultado por `LiveTranscriptionSignals`."""

    def __init__(
        self,
        image: Image.Image,
        language_code: str,
        tesseract_path: str | None,
        signals: LiveTranscriptionSignals,
        min_word_confidence: int = 0,
    ) -> None:
        """Guarda los parámetros de la transcripción a ejecutar en `run()`."""
        super().__init__()
        self.image = image
        self.language_code = language_code
        self.tesseract_path = tesseract_path
        self.min_word_confidence = min_word_confidence
        self.signals = signals

    def run(self) -> None:
        """Ejecuta la transcripción y emite `succeeded` o `failed` según el resultado."""
        try:
            result = transcribe_image_variants(
                self.image, self.language_code, self.tesseract_path, self.min_word_confidence
            )
        except Exception as error:
            self.signals.failed.emit(str(error))
        else:
            self.signals.succeeded.emit(result)


class ClaudeLiveTranscriptionSignals(QObject):
    """Señales emitidas por `ClaudeLiveTranscriptionRunnable` al terminar (los `QRunnable` no tienen señales propias)."""

    succeeded = Signal(str, int, int)  # texto, input_tokens, output_tokens
    failed = Signal(str)


class ClaudeLiveTranscriptionRunnable(QRunnable):
    """Corre `transcribe_image_claude` en un hilo del `QThreadPool` y emite el
    resultado por `ClaudeLiveTranscriptionSignals`. Mismo patrón que
    `LiveTranscriptionRunnable`, con la firma de tres valores de
    `transcribe_image_claude` (texto + tokens) y los errores del SDK
    `anthropic` ya traducidos vía `format_claude_error`.
    """

    def __init__(
        self,
        image: Image.Image,
        language_code: str,
        api_key: str,
        signals: ClaudeLiveTranscriptionSignals,
    ) -> None:
        """Guarda los parámetros de la transcripción a ejecutar en `run()`."""
        super().__init__()
        self.image = image
        self.language_code = language_code
        self.api_key = api_key
        self.signals = signals

    def run(self) -> None:
        """Ejecuta la transcripción y emite `succeeded` o `failed` según el resultado."""
        try:
            text, input_tokens, output_tokens = transcribe_image_claude(self.image, self.language_code, self.api_key)
        except Exception as error:
            self.signals.failed.emit(format_claude_error(error))
        else:
            self.signals.succeeded.emit(text, input_tokens, output_tokens)


class TranslationSignals(QObject):
    """Señales emitidas por `TranslationRunnable` al terminar (los `QRunnable` no tienen señales propias)."""

    translated = Signal(str)
    error = Signal(str)


class TranslationRunnable(QRunnable):
    """Corre `translate_text` en un hilo del `QThreadPool`. Mismo patrón que
    `LiveTranscriptionRunnable`: `run()` llama al model y emite `translated(str)`
    con el resultado o `error(str)` si `translate_text` levanta una excepción
    (ej. sin internet en la primera descarga del modelo).
    """

    def __init__(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        signals: TranslationSignals,
    ) -> None:
        """Guarda los parámetros de la traducción a ejecutar en `run()`."""
        super().__init__()
        self.text = text
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.signals = signals

    def run(self) -> None:
        """Ejecuta la traducción y emite `translated` o `error` según el resultado."""
        try:
            result = translate_text(self.text, self.source_lang, self.target_lang)
        except Exception as error:
            self.signals.error.emit(str(error))
        else:
            self.signals.translated.emit(result)


class LiveOcrController(QObject):
    """Orquesta el ciclo completo de OCR en vivo: crea/destruye `ScreenOverlay` vía
    `activate_selection()`, arranca/detiene el `QTimer` de polling vía
    `toggle_transcription()` (`QScreen.grabWindow` sobre `capture_geometry()`, que ya
    excluye el borde y la barra de controles del overlay -> diff de píxeles vía
    `model/image_diff.py` -> transcripción con Tesseract como detector de cambio
    de texto (`model/text_diff.py`) -> si el texto cambió y el motor es Claude
    con `live_claude_enabled`, dispara `transcribe_image_claude` en el
    `QThreadPool` global (con cooldown configurable) y muestra solo su
    resultado; en caso contrario, muestra el resultado de Tesseract),
    y actualiza `LiveOcrView` con cada captura/resultado. Propaga un estado
    (Detenido/Transcribiendo/Analizando…/Pausado) a la vista y al overlay en
    cada transición, y sincroniza el botón de traducción de ambos widgets.
    Instancia un `GlobalHotkeyManager` con vida igual a la de la app (persiste
    aunque se navegue afuera de la vista) para pausar/reanudar y cerrar el
    overlay con atajos globales de Windows, activos con o sin foco en la
    aplicación.
    Expone `stop()` para que `MainWindow` lo invoque al navegar afuera de la vista.
    """

    def __init__(self, view: LiveOcrView, main_window: "MainWindow | None" = None) -> None:
        """Registra la vista y conecta "Activar selección"/"Iniciar transcripción" a sus handlers.

        `main_window`, si se pasa, se usa para refrescar la barra de gasto
        (`refresh_spend_meter()`) tras cada llamada a Claude en el ciclo en vivo.
        """
        super().__init__()
        self.view = view
        self.main_window = main_window
        self._overlay: ScreenOverlay | None = None
        self._timer: QTimer | None = None
        self._previous_capture: Image.Image | None = None
        self._worker: LiveTranscriptionSignals | None = None
        self._tesseract_path: str | None = None
        self._min_word_confidence: int = 0
        self._text_similarity_threshold: int = 90
        self._pixel_change_sensitivity: int = 2
        self._last_detector_text: str | None = None
        self._engine: str = "tesseract"
        self._live_claude_enabled: bool = False
        self._claude_cooldown_seconds: int = 10
        self._api_key: str | None = None
        self._last_claude_call: float | None = None
        self._pending_capture: Image.Image | None = None
        self._claude_worker: ClaudeLiveTranscriptionSignals | None = None
        self._transcription_start: float = 0.0
        self._translation_active: bool = False
        self._translation_worker: TranslationSignals | None = None
        self._last_transcribed_text: str | None = None
        self._interacting: bool = False
        self._status: str = "Detenido"

        self._counter_timer = QTimer(self)
        self._counter_timer.timeout.connect(self._update_counter)

        self.view.activate_selection_clicked.connect(self.activate_selection)
        self.view.toggle_transcription_clicked.connect(self.toggle_transcription)
        self.view.translate_toggled.connect(self.on_translate_toggled)

        self._hotkey_manager = GlobalHotkeyManager(self)
        self._hotkey_manager.triggered.connect(self._on_hotkey_triggered)
        config = load_config()
        self._hotkey_toggle_text = config.get("hotkey_toggle", "Ctrl+Shift+P")
        self._hotkey_close_text = config.get("hotkey_close", "Ctrl+Shift+Q")
        self._hotkey_manager.register(HOTKEY_TOGGLE_ID, self._hotkey_toggle_text)
        self._hotkey_manager.register(HOTKEY_CLOSE_ID, self._hotkey_close_text)

    def _use_claude_live(self) -> bool:
        """Indica si el ciclo en vivo debe usar Claude (motor Claude + interruptor de vivo encendido)."""
        return self._engine == "claude" and self._live_claude_enabled

    def _set_status(self, status: str) -> None:
        """Actualiza `_status` y lo propaga a la vista y, si existe, al overlay.

        Args:
            status: uno de "Detenido", "Transcribiendo", "Analizando…" o "Pausado".
        """
        self._status = status
        self.view.set_status(status)
        if self._overlay is not None:
            self._overlay.set_status(status)

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
        self._last_detector_text = None
        self._last_claude_call = None
        self._pending_capture = None
        self._claude_worker = None
        self._interacting = False

        self._overlay = ScreenOverlay()
        self._overlay.closed.connect(self._on_overlay_closed)
        self._overlay.geometry_changed.connect(self._on_interaction_finished)
        self._overlay.interaction_started.connect(self._on_interaction_started)
        self._overlay.toggle_transcription_requested.connect(self.toggle_transcription)
        self._overlay.translate_toggle_requested.connect(self.on_translate_toggled)
        self._overlay.show()

        self.view.enable_transcription_button()
        self.view.set_transcription_button_running(False)
        self._overlay.set_toggle_enabled(True)
        self._overlay.set_running(False)
        self._overlay.set_translate_enabled(False)
        self._overlay.set_translate_active(self._translation_active)
        self._overlay.set_hotkey_labels(self._hotkey_toggle_text, self._hotkey_close_text)
        self._set_status("Detenido")

    def _disconnect_overlay_signals(self) -> None:
        """Desconecta las señales del overlay vigente antes de cerrarlo/descartarlo."""
        self._overlay.closed.disconnect(self._on_overlay_closed)
        self._overlay.geometry_changed.disconnect(self._on_interaction_finished)
        self._overlay.interaction_started.disconnect(self._on_interaction_started)
        self._overlay.toggle_transcription_requested.disconnect(self.toggle_transcription)
        self._overlay.translate_toggle_requested.disconnect(self.on_translate_toggled)

    def toggle_transcription(self) -> None:
        """Arranca o detiene el polling de transcripción según el estado actual del `QTimer`."""
        if self._timer is None:
            tesseract_path = resolve_tesseract_path()
            if tesseract_path is None:
                tesseract_path = prompt_tesseract_path(self.view)
                if tesseract_path is None:
                    return

            config = load_config()
            self._tesseract_path = tesseract_path
            self._min_word_confidence = config.get("min_word_confidence", 95)
            self._text_similarity_threshold = config.get("text_similarity_threshold", 90)
            self._pixel_change_sensitivity = config.get("pixel_change_sensitivity", 2)
            self._engine = config.get("engine", "tesseract")
            self._live_claude_enabled = config.get("live_claude_enabled", False)
            self._claude_cooldown_seconds = config.get("claude_cooldown_seconds", 10)
            self._api_key = None

            if self._use_claude_live():
                self._api_key = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
                if not self._api_key:
                    QMessageBox.critical(
                        self.view,
                        "Falta la API key",
                        "No hay una API key de Anthropic guardada. Configurala desde Configuración.",
                    )
                    return

            self._last_claude_call = None
            self._pending_capture = None

            self.view.set_transcription_button_running(True)
            if self._overlay is not None:
                self._overlay.set_running(True)
                self._overlay.set_translate_enabled(True)
            self._set_status("Transcribiendo")

            self._timer = QTimer(self)
            self._timer.timeout.connect(self._poll)
            self._timer.start(POLL_INTERVAL_MS)
            self._poll()
        else:
            self._timer.stop()
            self._timer = None
            self.view.set_transcription_button_running(False)
            if self._overlay is not None:
                self._overlay.set_running(False)
                self._overlay.set_translate_enabled(False)
            self._set_status("Pausado")

    def stop(self) -> None:
        """Detiene el polling y cierra/destruye el overlay si estaba activo."""
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

        self._counter_timer.stop()

        self._worker = None
        self._claude_worker = None
        self._pending_capture = None

        self._cancel_translation_worker()

        if self._overlay is not None:
            self._disconnect_overlay_signals()
            self._overlay.close()
            self._overlay = None

        self._previous_capture = None
        self._last_detector_text = None
        self._last_claude_call = None
        self._interacting = False
        self.view.enable_activate_button()
        self.view.disable_transcription_button()
        self.view.set_transcription_button_running(False)
        self._set_status("Detenido")

    def register_hotkey(self, hotkey_id: int, sequence_text: str) -> bool:
        """Reintenta registrar `sequence_text` bajo `hotkey_id` en el `GlobalHotkeyManager`.

        Si tiene éxito, actualiza el texto guardado y refresca el tooltip del
        overlay vigente (si existe). Usado por `SettingsController` al cambiar
        un atajo desde Configuración.
        """
        success = self._hotkey_manager.register(hotkey_id, sequence_text)
        if success:
            if hotkey_id == HOTKEY_TOGGLE_ID:
                self._hotkey_toggle_text = sequence_text
            elif hotkey_id == HOTKEY_CLOSE_ID:
                self._hotkey_close_text = sequence_text
            if self._overlay is not None:
                self._overlay.set_hotkey_labels(self._hotkey_toggle_text, self._hotkey_close_text)
        return success

    def _on_hotkey_triggered(self, hotkey_id: int) -> None:
        """Reacciona a un atajo global: pausa/reanuda la transcripción (creando el
        overlay y arrancando si no existía) o cierra el overlay, según `hotkey_id`.
        """
        if hotkey_id == HOTKEY_TOGGLE_ID:
            if self._overlay is None:
                self.activate_selection()
            self.toggle_transcription()
        elif hotkey_id == HOTKEY_CLOSE_ID:
            if self._overlay is not None:
                self._overlay.request_close()

    def _on_overlay_closed(self) -> None:
        """Detiene el polling al cerrar el overlay con la X, sin tocar el resto del estado."""
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self._counter_timer.stop()
        self._claude_worker = None
        self._pending_capture = None
        self._cancel_translation_worker()
        self._overlay = None
        self._previous_capture = None
        self._last_detector_text = None
        self._last_claude_call = None
        self._interacting = False
        self.view.enable_activate_button()
        self.view.disable_transcription_button()
        self.view.set_transcription_button_running(False)
        self._set_status("Detenido")

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
        """Descarta cualquier `TranslationRunnable` en curso sin limpiar el texto ya mostrado."""
        self._translation_worker = None

    def _poll(self) -> None:
        """Captura el área del overlay, actualiza la miniatura y dispara transcripción si cambió.

        Antes de capturar, despacha la llamada a Claude pendiente por cooldown
        (`_pending_capture`) si ya venció, con el contenido más reciente.
        """
        if self._overlay is None or self._timer is None or self._interacting:
            return

        if self._pending_capture is not None and self._cooldown_elapsed():
            pending_capture = self._pending_capture
            self._pending_capture = None
            self._dispatch_claude_call(pending_capture)

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
        if not has_changed(self._previous_capture, current, self._pixel_change_sensitivity / 100):
            return

        self._previous_capture = current
        self._start_transcription(current)

    def _update_thumbnail(self, pixmap: QPixmap) -> None:
        """Reescala `pixmap` al tamaño del recuadro de miniatura y lo muestra en la vista."""
        label = self.view.preview_label
        scaled = pixmap.scaled(label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.view.set_preview_image(scaled)

    def _start_transcription(self, image: Image.Image) -> None:
        """Lanza la transcripción de `image` en el `QThreadPool` global, reemplazando el worker vigente."""
        self._set_status("Analizando…")
        language_code = LANGUAGE_MAP[self.view.get_selected_language()]

        self._transcription_start = time.monotonic()
        self._update_counter()
        signals = LiveTranscriptionSignals(self)
        signals.succeeded.connect(self._on_transcription_succeeded)
        signals.failed.connect(self._on_transcription_failed)
        self._worker = signals
        runnable = LiveTranscriptionRunnable(
            image, language_code, self._tesseract_path, signals, self._min_word_confidence
        )
        QThreadPool.globalInstance().start(runnable)
        self._counter_timer.start(COUNTER_INTERVAL_MS)

    def _update_counter(self) -> None:
        """Actualiza el contador de segundos mientras la transcripción está en curso."""
        self.view.set_result_text(processing_label(self._transcription_start))

    def _on_transcription_succeeded(self, text: str) -> None:
        """Procesa el resultado del detector de Tesseract si proviene del worker
        vigente; descarta resultados obsoletos.

        Descarta el resultado si el texto es equivalente al último aceptado
        (`has_text_changed`), evitando refrescar la vista y re-disparar la
        traducción por ruido visual que no cambia el contenido reconocido. Si
        el texto cambió y el ciclo en vivo usa Claude, dispara (o encola) la
        llamada a Claude en vez de mostrar el texto de Tesseract.
        """
        if self.sender() is not self._worker:
            self.sender().deleteLater()
            return
        self._counter_timer.stop()
        self._worker.deleteLater()
        self._worker = None
        self._set_status("Transcribiendo")

        if not has_text_changed(self._last_detector_text, text, self._text_similarity_threshold):
            return

        self._last_detector_text = text

        if self._use_claude_live():
            self._handle_claude_trigger(self._previous_capture)
            return

        self.view.set_result_text(text)
        self._last_transcribed_text = text
        if self._translation_active:
            self._start_translation(text)

    def _on_transcription_failed(self, error_message: str) -> None:
        """Muestra el error si proviene del worker vigente; descarta fallos obsoletos."""
        if self.sender() is not self._worker:
            self.sender().deleteLater()
            return
        self._counter_timer.stop()
        self._worker.deleteLater()
        self._worker = None
        self._set_status("Transcribiendo")
        QMessageBox.critical(self.view, "Error al transcribir", error_message)

    def _cooldown_elapsed(self) -> bool:
        """Indica si ya pasó `_claude_cooldown_seconds` desde la última llamada a Claude."""
        if self._last_claude_call is None:
            return True
        return (time.monotonic() - self._last_claude_call) >= self._claude_cooldown_seconds

    def _handle_claude_trigger(self, image: Image.Image) -> None:
        """Dispara la llamada a Claude si el cooldown ya venció; si no, encola
        `image` en `_pending_capture` para despacharla en el primer `_poll`
        posterior al vencimiento, reemplazando cualquier captura pendiente
        anterior (se envía siempre el contenido más reciente).
        """
        if self._cooldown_elapsed():
            self._dispatch_claude_call(image)
        else:
            self._pending_capture = image

    def _dispatch_claude_call(self, image: Image.Image) -> None:
        """Lanza `transcribe_image_claude` en el `QThreadPool` global y arranca
        el contador de segundos mientras se espera la respuesta.
        """
        self._set_status("Analizando…")
        self._last_claude_call = time.monotonic()
        language_code = LANGUAGE_MAP[self.view.get_selected_language()]

        self._transcription_start = time.monotonic()
        self._update_counter()
        signals = ClaudeLiveTranscriptionSignals(self)
        signals.succeeded.connect(self._on_claude_succeeded)
        signals.failed.connect(self._on_claude_failed)
        self._claude_worker = signals
        runnable = ClaudeLiveTranscriptionRunnable(image, language_code, self._api_key, signals)
        QThreadPool.globalInstance().start(runnable)
        self._counter_timer.start(COUNTER_INTERVAL_MS)

    def _on_claude_succeeded(self, text: str, input_tokens: int, output_tokens: int) -> None:
        """Muestra el resultado de Claude si proviene del worker vigente; descarta
        resultados obsoletos. Registra el gasto y refresca la barra de `MainWindow`.
        """
        if self.sender() is not self._claude_worker:
            self.sender().deleteLater()
            return
        self._counter_timer.stop()
        self._claude_worker.deleteLater()
        self._claude_worker = None
        self._set_status("Transcribiendo")

        register_call(input_tokens, output_tokens)
        if self.main_window is not None:
            self.main_window.refresh_spend_meter()

        self.view.set_result_text(text)
        self._last_transcribed_text = text
        if self._translation_active:
            self._start_translation(text)

    def _on_claude_failed(self, error_message: str) -> None:
        """Detiene el polling y avisa una única vez ante un error de la API de
        Claude, en vez de repetirlo en cada tick o caer a Tesseract en silencio.
        """
        if self.sender() is not self._claude_worker:
            self.sender().deleteLater()
            return
        self._counter_timer.stop()
        self._claude_worker.deleteLater()
        self._claude_worker = None
        self._pending_capture = None

        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self.view.set_transcription_button_running(False)
        if self._overlay is not None:
            self._overlay.set_running(False)
            self._overlay.set_translate_enabled(False)
        self._set_status("Pausado")

        QMessageBox.critical(self.view, "Error al transcribir con Claude", error_message)

    def on_translate_toggled(self) -> None:
        """Alterna `_translation_active`; al activar, traduce el texto ya reconocido si existe.

        Conectado tanto a `translate_toggled` de `LiveOcrView` como a
        `translate_toggle_requested` del overlay: cualquiera de los dos botones
        dispara este mismo handler, que sincroniza el estado marcado de ambos.
        """
        self._translation_active = not self._translation_active
        self.view.set_translation_button_active(self._translation_active)
        if self._overlay is not None:
            self._overlay.set_translate_active(self._translation_active)
        if self._translation_active and self._last_transcribed_text:
            self._start_translation(self._last_transcribed_text)

    def _start_translation(self, text: str) -> None:
        """Lanza la traducción de `text` en el `QThreadPool` global, reemplazando el worker vigente."""
        source_lang = LANGUAGE_MAP[self.view.get_source_language()]
        target_lang = LANGUAGE_MAP[self.view.get_target_language()]

        self.view.set_translated_text("Traduciendo...")
        signals = TranslationSignals(self)
        signals.translated.connect(self._on_translation_finished)
        signals.error.connect(self._on_translation_error)
        self._translation_worker = signals
        runnable = TranslationRunnable(text, source_lang, target_lang, signals)
        QThreadPool.globalInstance().start(runnable)

    def _on_translation_finished(self, translated_text: str) -> None:
        """Muestra la traducción si proviene del worker vigente; descarta resultados obsoletos."""
        if self.sender() is not self._translation_worker:
            self.sender().deleteLater()
            return
        self._translation_worker.deleteLater()
        self._translation_worker = None
        self.view.set_translated_text(translated_text)

    def _on_translation_error(self, error_message: str) -> None:
        """Muestra el error si proviene del worker vigente; el polling sigue sin interrupciones."""
        if self.sender() is not self._translation_worker:
            self.sender().deleteLater()
            return
        self._translation_worker.deleteLater()
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
