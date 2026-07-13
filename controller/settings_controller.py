"""Conecta los eventos de SettingsView con el Model y con MainWindow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from model.config_model import save_theme
from view.settings_view import SettingsView

if TYPE_CHECKING:
    from view.main_window import MainWindow


class SettingsController:
    """Conecta SettingsView con el Model: al recibir `theme_toggled`, llama a
    save_theme() y le pide a MainWindow reaplicar el tema en caliente
    (paleta + stylesheet) sobre toda la ventana.
    """

    def __init__(self, settings_view: SettingsView, main_window: "MainWindow") -> None:
        """Guarda las referencias a la vista y la ventana, y conecta la señal de tema."""
        self.settings_view = settings_view
        self.main_window = main_window

        self.settings_view.theme_toggled.connect(self._on_theme_toggled)

    def _on_theme_toggled(self, theme: str) -> None:
        """Persiste el tema elegido y lo reaplica en caliente sobre la ventana."""
        save_theme(theme)
        self.main_window.apply_theme(theme)
