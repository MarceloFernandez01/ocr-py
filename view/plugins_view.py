"""Vista "Plugins" (PySide6): lista, activa/desactiva, configura y recarga los plugins instalados."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from model.plugin_registry import LoadedPlugin


class PluginsView(QWidget):
    """Sin lógica de negocio: solo presentación y señales.

    `set_plugins` repuebla la lista completa (nombre, versión, descripción,
    capacidades y estado, con badge "Esencial" para los tres plugins
    nativos). El acordeón de ajustes y el interruptor de activar/desactivar
    para plugins no esenciales se agregan en el paso siguiente de la spec.
    """

    reload_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el banner de instalación corrupta, el botón de recarga y la lista."""
        super().__init__(parent)

        self.corrupt_banner = QLabel()
        self.corrupt_banner.setObjectName("pluginsCorruptBanner")
        self.corrupt_banner.setWordWrap(True)
        self.corrupt_banner.setVisible(False)

        self.reload_button = QPushButton("Recargar plugins")
        self.reload_button.setObjectName("pluginsReloadButton")
        self.reload_button.clicked.connect(self.reload_requested.emit)

        header_row = QHBoxLayout()
        header_row.addStretch()
        header_row.addWidget(self.reload_button)

        self._list_layout = QVBoxLayout()
        self._list_layout.setAlignment(Qt.AlignTop)

        list_container = QWidget()
        list_container.setLayout(self._list_layout)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("pluginsScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(list_container)

        layout = QVBoxLayout(self)
        layout.addLayout(header_row)
        layout.addWidget(self.corrupt_banner)
        layout.addWidget(scroll_area)

        self._rows: dict[str, QWidget] = {}

    def set_plugins(self, loaded_plugins: list["LoadedPlugin"]) -> None:
        """Repuebla la lista completa a partir de `loaded_plugins`."""
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._rows = {}

        for plugin in loaded_plugins:
            row = self._build_row(plugin)
            self._list_layout.addWidget(row)
            self._rows[plugin.id] = row

    def _build_row(self, plugin: "LoadedPlugin") -> QWidget:
        """Construye la fila de `plugin`: nombre, versión, badge esencial,
        capacidades, descripción y estado (con el mensaje de error si aplica).
        """
        row = QFrame()
        row.setObjectName("pluginRow")
        row_layout = QVBoxLayout(row)

        header = QHBoxLayout()
        title = plugin.name if not plugin.version else f"{plugin.name} — v{plugin.version}"
        name_label = QLabel(title)
        name_label.setObjectName("pluginName")
        header.addWidget(name_label)

        if plugin.essential:
            badge = QLabel("Esencial")
            badge.setObjectName("pluginEssentialBadge")
            header.addWidget(badge)

        header.addStretch()
        row_layout.addLayout(header)

        capabilities_label = QLabel(", ".join(plugin.provides) if plugin.provides else "—")
        capabilities_label.setObjectName("pluginCapabilities")
        row_layout.addWidget(capabilities_label)

        status_label = QLabel(self._status_text(plugin))
        status_label.setObjectName("pluginStatus")
        status_label.setWordWrap(True)
        row_layout.addWidget(status_label)

        return row

    @staticmethod
    def _status_text(plugin: "LoadedPlugin") -> str:
        """Texto de estado de `plugin`: mensaje de error, o Activo/Deshabilitado."""
        if plugin.error is not None:
            return f"Con error: {plugin.error}"
        return "Activo" if plugin.enabled else "Deshabilitado"

    def set_corrupt_banner(self, missing_ids: list[str]) -> None:
        """Muestra u oculta el banner de instalación corrupta según `missing_ids`."""
        if not missing_ids:
            self.corrupt_banner.setVisible(False)
            self.corrupt_banner.clear()
            return

        ids_text = ", ".join(missing_ids)
        self.corrupt_banner.setText(
            f"Instalación de plugins incompleta: falta el plugin esencial «{ids_text}»."
            if len(missing_ids) == 1
            else f"Instalación de plugins incompleta: faltan los plugins esenciales «{ids_text}»."
        )
        self.corrupt_banner.setVisible(True)

    def set_reload_enabled(self, enabled: bool) -> None:
        """Habilita o deshabilita el botón "Recargar plugins"."""
        self.reload_button.setEnabled(enabled)
