"""Conecta PluginsView con model/plugin_registry.py: listar, activar/desactivar, ajustar y recargar plugins."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from model.plugin_registry import (
    LoadedPlugin,
    get_plugins,
    missing_essentials,
    reload_plugins,
    resolve_setting_value,
    save_setting_value,
    set_enabled,
)
from view.plugins_view import PluginsView

if TYPE_CHECKING:
    from view.main_window import MainWindow


class PluginsController:
    """Puebla `PluginsView` desde el registro de plugins y persiste sus cambios.

    Se repuebla al mostrarse la vista (señal `plugins_selected` del sidebar,
    conectada en `__init__`) y después de cada recarga. El botón "Recargar
    plugins" queda deshabilitado mientras haya una transcripción de imagen
    (`main_window.ocr_controller.state.transcription_in_progress`) o de OCR
    en vivo (`main_window.live_ocr_controller._status != "Detenido"`) en curso.
    """

    def __init__(self, view: PluginsView, main_window: MainWindow) -> None:
        """Conecta las señales de `view` y la señal `plugins_selected` del sidebar."""
        self.view = view
        self.main_window = main_window

        self.view.reload_requested.connect(self._on_reload_requested)
        self.view.plugin_enabled_toggled.connect(self._on_plugin_enabled_toggled)
        self.view.plugin_setting_changed.connect(self._on_plugin_setting_changed)
        self.main_window.sidebar_view.plugins_selected.connect(self.refresh)

    def refresh(self) -> None:
        """Puebla la vista con el estado actual del registro, sin reimportar módulos."""
        self.view.set_plugins([self._with_resolved_settings(plugin) for plugin in get_plugins()])
        self.view.set_corrupt_banner(missing_essentials())
        self.view.set_reload_enabled(self._can_reload())

    @staticmethod
    def _with_resolved_settings(plugin: LoadedPlugin) -> LoadedPlugin:
        """Copia de `plugin` con `SettingField.default` reemplazado por el valor
        vigente (`resolve_setting_value`), para que el acordeón muestre el
        valor persistido en vez del default estático del manifiesto.
        """
        resolved_fields = [
            replace(field, default=resolve_setting_value(plugin.id, field.key)) for field in plugin.settings
        ]
        return replace(plugin, settings=resolved_fields)

    def _can_reload(self) -> bool:
        """Indica si "Recargar plugins" debe estar habilitado: sin transcripciones en curso."""
        ocr_controller = getattr(self.main_window, "ocr_controller", None)
        transcribing = ocr_controller is not None and ocr_controller.state.transcription_in_progress
        live_running = self.main_window.live_ocr_controller._status != "Detenido"
        return not transcribing and not live_running

    def _on_reload_requested(self) -> None:
        """Recarga el registro y repuebla la vista y los combos de `SettingsView`.

        El botón ya debería estar deshabilitado mientras no se puede
        recargar; esta comprobación es un resguardo adicional.
        """
        if not self._can_reload():
            return
        reload_plugins()
        self.refresh()
        self.main_window.settings_view.refresh_engine_combos()

    def _on_plugin_enabled_toggled(self, plugin_id: str, enabled: bool) -> None:
        """Persiste el nuevo estado de `plugin_id` y repuebla la vista."""
        set_enabled(plugin_id, enabled)
        self.refresh()

    def _on_plugin_setting_changed(self, plugin_id: str, field_key: str, value: object) -> None:
        """Persiste el valor nuevo del campo, sin repoblar la vista."""
        save_setting_value(plugin_id, field_key, value)
