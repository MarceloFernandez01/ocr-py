"""Conecta los eventos de SettingsView con el Model y con MainWindow."""

from __future__ import annotations

from typing import TYPE_CHECKING

import keyring
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from controller.common import KEYRING_SERVICE, KEYRING_USERNAME
from model.config_model import load_config, save_engine, save_theme
from view.settings_view import SettingsView

if TYPE_CHECKING:
    from view.main_window import MainWindow


class SettingsController:
    """Conecta SettingsView con el Model: al recibir `theme_toggled`, llama a
    save_theme() y le pide a MainWindow reaplicar el tema en caliente
    (paleta + stylesheet) sobre toda la ventana. También gestiona la
    selección de motor OCR y la carga/reemplazo de la API key de Anthropic
    en el keyring del sistema operativo.
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
                "Ingresá tu API key de Anthropic para usar Claude Haiku como motor OCR:",
                echo=QLineEdit.Password,
            )
            if not ok or not key:
                self.settings_view.set_engine_silent("tesseract")
                return

            if not self._save_api_key(key):
                self.settings_view.set_engine_silent("tesseract")
                save_engine("tesseract")
                return

        save_engine(engine)

    def _on_api_key_submitted(self, key: str) -> None:
        """Guarda la key reemplazada vía el botón "Cambiar" y persiste el motor Claude."""
        if self._save_api_key(key):
            save_engine("claude")
        else:
            self.settings_view.set_engine_silent("tesseract")
            save_engine("tesseract")

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
