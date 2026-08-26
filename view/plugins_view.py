"""Vista "Plugins" (PySide6): lista, activa/desactiva, configura y recarga los plugins instalados."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from view.settings_view import ThemeSwitch

if TYPE_CHECKING:
    from model.plugin_manifest import SettingField
    from model.plugin_registry import LoadedPlugin


def _parse_number(text: str) -> object:
    """Convierte `text` a `int` o `float`; devuelve el texto sin tocar si no es numérico."""
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return text


class PluginsView(QWidget):
    """Sin lógica de negocio: solo presentación y señales.

    `set_plugins` repuebla la lista completa (nombre, versión, descripción,
    capacidades, estado, badge "Esencial" para los tres plugins nativos,
    interruptor de activar/desactivar para los demás, y un acordeón por
    plugin con sus campos de `settings`). Los campos y el interruptor
    persisten al cambiar de valor, sin botón "Guardar" explícito, igual que
    el resto de `SettingsView`.
    """

    reload_requested = Signal()
    plugin_enabled_toggled = Signal(str, bool)
    plugin_setting_changed = Signal(str, str, object)

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
        self._list_layout.setSpacing(10)

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

    def set_plugins(self, loaded_plugins: list[LoadedPlugin]) -> None:
        """Repuebla la lista completa a partir de `loaded_plugins`.

        El valor mostrado en cada campo del acordeón es `SettingField.default`
        tal como venga en `loaded_plugins`: el controller es responsable de
        pasar ahí el valor ya resuelto (`resolve_setting_value`), no el
        default estático del manifiesto, para que el acordeón muestre el
        valor vigente.
        """
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

    def _build_row(self, plugin: LoadedPlugin) -> QWidget:
        """Construye la fila de `plugin`: nombre, versión, badge esencial,
        interruptor (si no es esencial), capacidades, descripción, estado
        (con el mensaje de error si aplica) y el acordeón de ajustes.
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

        if not plugin.essential:
            enabled_switch = ThemeSwitch()
            enabled_switch.set_checked_silent(plugin.enabled)
            enabled_switch.toggled.connect(
                lambda checked, plugin_id=plugin.id: self.plugin_enabled_toggled.emit(plugin_id, checked)
            )
            header.addWidget(enabled_switch)

        row_layout.addLayout(header)

        if plugin.description:
            description_label = QLabel(plugin.description)
            description_label.setObjectName("pluginDescription")
            description_label.setWordWrap(True)
            row_layout.addWidget(description_label)

        capabilities_label = QLabel(", ".join(plugin.provides) if plugin.provides else "—")
        capabilities_label.setObjectName("pluginCapabilities")
        row_layout.addWidget(capabilities_label)

        status_label = QLabel(self._status_text(plugin))
        status_label.setObjectName("pluginStatus")
        status_label.setProperty("state", self._status_state(plugin))
        status_label.setWordWrap(True)
        row_layout.addWidget(status_label)

        if plugin.settings:
            row_layout.addWidget(self._build_settings_accordion(plugin))

        return row

    def _build_settings_accordion(self, plugin: LoadedPlugin) -> QWidget:
        """Botón expandir/colapsar + contenedor con un campo por cada `SettingField` de `plugin`."""
        toggle_button = QPushButton("Ajustes ▸")
        toggle_button.setObjectName("pluginSettingsToggle")
        toggle_button.setCheckable(True)
        toggle_button.setChecked(False)

        fields_container = QWidget()
        fields_container.setObjectName("pluginSettingsAccordion")
        fields_layout = QVBoxLayout(fields_container)
        for setting_field in plugin.settings:
            fields_layout.addWidget(self._build_settings_field(plugin.id, setting_field))
        fields_container.setVisible(False)

        def _on_toggled(checked: bool) -> None:
            toggle_button.setText("Ajustes ▾" if checked else "Ajustes ▸")
            fields_container.setVisible(checked)

        toggle_button.toggled.connect(_on_toggled)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(toggle_button)
        wrapper_layout.addWidget(fields_container)
        return wrapper

    def _build_settings_field(self, plugin_id: str, setting_field: SettingField) -> QWidget:
        """Fila con la etiqueta y el widget de entrada del campo `setting_field`, según su tipo."""
        row = QHBoxLayout()
        label = QLabel(setting_field.label)
        row.addWidget(label)

        if setting_field.type == "boolean":
            switch = ThemeSwitch()
            switch.set_checked_silent(bool(setting_field.default))
            switch.toggled.connect(
                lambda checked, pid=plugin_id, key=setting_field.key: self.plugin_setting_changed.emit(
                    pid, key, checked
                )
            )
            row.addWidget(switch)
        else:
            line_edit = QLineEdit()
            if setting_field.type == "api_key":
                line_edit.setEchoMode(QLineEdit.Password)
            line_edit.setText("" if setting_field.default is None else str(setting_field.default))
            field_type = setting_field.type

            def _on_finished(pid=plugin_id, key=setting_field.key, edit=line_edit, ftype=field_type) -> None:
                value = edit.text()
                if ftype == "number":
                    value = _parse_number(value)
                self.plugin_setting_changed.emit(pid, key, value)

            line_edit.editingFinished.connect(_on_finished)
            row.addWidget(line_edit)

        container = QWidget()
        container.setLayout(row)
        return container

    @staticmethod
    def _status_text(plugin: LoadedPlugin) -> str:
        """Texto de estado de `plugin`: mensaje de error, o Activo/Deshabilitado."""
        if plugin.error is not None:
            return f"Con error: {plugin.error}"
        return "Activo" if plugin.enabled else "Deshabilitado"

    @staticmethod
    def _status_state(plugin: LoadedPlugin) -> str:
        """Propiedad Qt dinámica (`state`) que `metro_style.py` usa para colorear
        `pluginStatus` según corresponda: "error", "active" o "disabled".
        """
        if plugin.error is not None:
            return "error"
        return "active" if plugin.enabled else "disabled"

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
