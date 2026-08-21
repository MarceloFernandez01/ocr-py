"""Conecta los eventos de SettingsView con el Model y con MainWindow."""

from __future__ import annotations

from typing import TYPE_CHECKING

import keyring
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from controller.common import KEYRING_SERVICE, KEYRING_USERNAME
from controller.global_hotkeys import HOTKEY_CLOSE_ID, HOTKEY_TOGGLE_ID
from model.config_model import (
    load_config,
    save_claude_cooldown_seconds,
    save_claude_monthly_budget_usd,
    save_engine,
    save_hotkey_close,
    save_hotkey_toggle,
    save_live_claude_enabled,
    save_min_word_confidence,
    save_pixel_change_sensitivity,
    save_text_similarity_threshold,
    save_theme,
)
from model.hotkey_model import has_modifier
from view.settings_view import SettingsView

if TYPE_CHECKING:
    from view.main_window import MainWindow


class SettingsController:
    """Conecta SettingsView con el Model: al recibir `theme_toggled`, llama a
    save_theme() y le pide a MainWindow reaplicar el tema en caliente
    (paleta + stylesheet) sobre toda la ventana. También gestiona la
    selección de motor OCR, la carga/reemplazo de la API key de Anthropic
    en el keyring del sistema operativo, la persistencia del umbral de
    confianza mínima por palabra del filtro de ruido de Tesseract, y la
    persistencia de los controles de OCR en vivo (interruptor de Claude,
    sensibilidad de texto/píxeles, cooldown y presupuesto mensual), y la
    validación/registro de los atajos globales (delegado en
    `LiveOcrController.register_hotkey()`, vía `main_window`).
    """

    def __init__(self, settings_view: SettingsView, main_window: "MainWindow") -> None:
        """Guarda las referencias a la vista y la ventana, conecta las señales
        y sincroniza el estado inicial del motor OCR y la API key guardada.
        """
        self.settings_view = settings_view
        self.main_window = main_window

        self.settings_view.theme_toggled.connect(self._on_theme_toggled)
        self.settings_view.engine_changed.connect(self._on_engine_changed)
        self.settings_view.api_key_submitted.connect(self._on_api_key_submitted)
        self.settings_view.min_word_confidence_changed.connect(save_min_word_confidence)
        self.settings_view.live_claude_toggled.connect(save_live_claude_enabled)
        self.settings_view.text_similarity_threshold_changed.connect(save_text_similarity_threshold)
        self.settings_view.pixel_change_sensitivity_changed.connect(save_pixel_change_sensitivity)
        self.settings_view.claude_cooldown_changed.connect(save_claude_cooldown_seconds)
        self.settings_view.claude_budget_changed.connect(save_claude_monthly_budget_usd)
        self.settings_view.hotkey_toggle_changed.connect(self._on_hotkey_toggle_changed)
        self.settings_view.hotkey_close_changed.connect(self._on_hotkey_close_changed)

        self._sync_initial_state()

    def _sync_initial_state(self) -> None:
        """Refleja en la vista el motor persistido en config.json y si ya
        hay una API key guardada en el keyring, sin emitir señales.
        """
        engine = load_config().get("engine", "tesseract")
        self.settings_view.set_engine_silent(engine)
        self.settings_view.set_api_key_saved(self._get_saved_api_key() is not None)

    def _get_saved_api_key(self) -> str | None:
        """Lee la API key de Anthropic del keyring; None si no hay o el keyring falla al leer."""
        try:
            return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        except Exception:
            return None

    def _on_theme_toggled(self, theme: str) -> None:
        """Persiste el tema elegido y lo reaplica en caliente sobre la ventana."""
        save_theme(theme)
        self.main_window.apply_theme(theme)

    def _on_engine_changed(self, engine: str) -> None:
        """Si se elige Claude sin key guardada, bloquea la selección y pide la
        key vía diálogo; si se cancela o el guardado falla, revierte a
        Tesseract. En cualquier otro caso, persiste el motor elegido.
        """
        if engine == "claude" and self._get_saved_api_key() is None:
            key, ok = QInputDialog.getText(
                self.settings_view,
                "API key de Anthropic",
                "Ingrese su API key de Anthropic para usar Claude Haiku como motor OCR:",
                echo=QLineEdit.Password,
            )
            if not ok or not key:
                self.settings_view.set_engine_silent("tesseract")
                return

            if not self._save_api_key(key):
                self.settings_view.set_engine_silent("tesseract")
                save_engine("tesseract")
                self.main_window.refresh_spend_meter()
                return

        save_engine(engine)
        self.main_window.refresh_spend_meter()

    def _on_api_key_submitted(self, key: str) -> None:
        """Guarda la key reemplazada vía el botón "Cambiar" y persiste el motor Claude."""
        if self._save_api_key(key):
            save_engine("claude")
        else:
            self.settings_view.set_engine_silent("tesseract")
            save_engine("tesseract")
        self.main_window.refresh_spend_meter()

    def _save_api_key(self, key: str) -> bool:
        """Guarda `key` en el keyring del SO y enmascara el campo en la vista.

        Devuelve False (y muestra un QMessageBox) si el keyring falla al guardar.
        """
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, key)
        except Exception as error:
            QMessageBox.critical(
                self.settings_view,
                "Error de keyring",
                f"No se pudo guardar la API key en el keyring del sistema: {error}",
            )
            return False

        self.settings_view.set_api_key_saved(True)
        return True

    def _on_hotkey_toggle_changed(self, sequence_text: str) -> None:
        """Valida y re-registra el atajo de pausar/reanudar; persiste si tiene éxito."""
        self._apply_hotkey_change(
            hotkey_id=HOTKEY_TOGGLE_ID,
            sequence_text=sequence_text,
            default="Ctrl+Shift+P",
            config_key="hotkey_toggle",
            save_fn=save_hotkey_toggle,
            revert_fn=self.settings_view.set_hotkey_toggle_silent,
        )

    def _on_hotkey_close_changed(self, sequence_text: str) -> None:
        """Valida y re-registra el atajo de cerrar overlay; persiste si tiene éxito."""
        self._apply_hotkey_change(
            hotkey_id=HOTKEY_CLOSE_ID,
            sequence_text=sequence_text,
            default="Ctrl+Shift+Q",
            config_key="hotkey_close",
            save_fn=save_hotkey_close,
            revert_fn=self.settings_view.set_hotkey_close_silent,
        )

    def _apply_hotkey_change(
        self,
        hotkey_id: int,
        sequence_text: str,
        default: str,
        config_key: str,
        save_fn,
        revert_fn,
    ) -> None:
        """Valida `sequence_text` y la reintenta registrar en `LiveOcrController`;
        si la validación o el registro fallan, revierte el campo al valor
        persistido y muestra el aviso correspondiente, sin persistir el cambio.
        """
        if not has_modifier(sequence_text):
            revert_fn(load_config().get(config_key, default))
            self.settings_view.set_hotkey_warning(
                "El atajo debe incluir al menos un modificador (Ctrl, Alt o Shift)."
            )
            return

        if not self.main_window.live_ocr_controller.register_hotkey(hotkey_id, sequence_text):
            revert_fn(load_config().get(config_key, default))
            self.settings_view.set_hotkey_warning(
                "Windows no pudo registrar el atajo: probablemente otra aplicación ya lo usa."
            )
            return

        save_fn(sequence_text)
        self.settings_view.set_hotkey_warning("")
