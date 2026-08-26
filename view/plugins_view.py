"""Vista "Plugins" (PySide6): lista, activa/desactiva, configura y recarga los plugins instalados."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget


class PluginsView(QWidget):
    """Vista sin lógica de negocio, solo presentación y señales.

    En este paso es un panel vacío: `set_plugins`, `set_corrupt_banner`,
    `set_reload_enabled` y las señales (`reload_requested`,
    `plugin_enabled_toggled`, `plugin_setting_changed`) se agregan en los
    pasos siguientes de la spec.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el layout base de la vista."""
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
