"""Descubrimiento, carga y despacho de plugins de OCR, traducción y preprocesamiento.

No importa PySide6. Escanea `plugins_core/` (esenciales, distribuidos con la
app) y `plugins/` (de terceros), valida cada manifiesto con
`model/plugin_manifest.py`, importa el módulo de cada plugin de forma
aislada y expone un índice por capacidad para que los controladores pidan
"el proveedor de OCR con id X" sin conocer motores concretos.
"""

import importlib.util
import json
import os
import sys
from dataclasses import dataclass, field

import keyring

from model.config_model import (
    KEYRING_SERVICE,
    KEYRING_USERNAME,
    load_config,
    plugin_keyring_username,
    save_plugin_enabled,
    save_plugin_setting_field,
)
from model.plugin_manifest import CAPABILITY_FUNCTIONS, SettingField, parse_manifest

if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CORE_PLUGINS_DIR = os.path.join(_BASE_DIR, "plugins_core")
USER_PLUGINS_DIR = os.path.join(_BASE_DIR, "plugins")

# Ids que deben existir en CORE_PLUGINS_DIR. Un plugin de plugins/ con uno de
# estos ids de carpeta se descarta: el id queda reservado para el esencial,
# esté o no cargado, así ningún plugin de terceros puede volverse esencial.
ESSENTIAL_PLUGIN_IDS = ("tesseract", "claude", "argos")

# Capacidades que tienen un proveedor seleccionado en config.json y que por
# lo tanto gobierna la regla de desactivación de un esencial.
SELECTABLE_CAPABILITIES = ("ocr", "translation")

_CAPABILITY_NOUN = {"ocr": "motor de OCR", "translation": "traductor"}
_CAPABILITY_SHORT_NOUN = {"ocr": "motor", "translation": "traductor"}


@dataclass
class LoadedPlugin:
    """Resultado de intentar cargar un plugin, exitoso o no."""

    id: str
    name: str
    version: str
    provides: list[str]
    module: object | None
    error: str | None
    enabled: bool
    essential: bool
    settings: list[SettingField] = field(default_factory=list)


class PluginError(Exception):
    """Envuelve una excepción de un plugin para mostrarla nombrando el plugin."""

    def __init__(self, plugin_name: str, original: Exception):
        self.plugin_name = plugin_name
        self.original = original
        super().__init__(f"El plugin «{plugin_name}» falló: {original}")

    def __str__(self) -> str:
        return f"El plugin «{self.plugin_name}» falló: {self.original}"


class PluginContext:
    """Superficie que la aplicación le presta a un plugin durante su ejecución.

    Es la única forma en que un plugin accede a funcionalidad de la app: no
    necesita importar nada de `model/`, `view/` ni `controller/`.
    """

    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def preprocess(self, image) -> list[tuple[str, "object"]]:
        """Devuelve las variantes nativas de preprocesamiento más las de plugins activos."""
        from model.image_preprocessing import generate_variants

        variants = list(generate_variants(image))
        for plugin in list_providers("preprocessing"):
            try:
                variants.extend(plugin.module.preprocess(image, _plugin_settings(plugin.id)))
            except Exception:
                # Un plugin de preprocesamiento roto no debe tumbar la
                # transcripción entera: se descartan sus variantes y siguen
                # las demás (nativas u otros plugins).
                continue
        return variants


_plugins_cache: list[LoadedPlugin] | None = None


def _list_subfolders(directory: str) -> list[str]:
    """Nombres de subcarpetas de `directory`, en orden alfabético; `[]` si no existe."""
    if not os.path.isdir(directory):
        return []
    return sorted(
        name
        for name in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, name))
    )


def _plugin_config(plugin_id: str, plugin_settings: dict) -> dict:
    """Entrada de `config.json["plugins"][plugin_id]`, o `{}` si no figura."""
    return plugin_settings.get(plugin_id, {})


def _plugin_settings(plugin_id: str) -> dict:
    """Ajustes propios de `plugin_id`, leídos de `config.json["plugins"][id]["settings"]`."""
    config = load_config()
    return _plugin_config(plugin_id, config.get("plugins", {})).get("settings", {})


def _load_plugin_folder(base_dir: str, folder_name: str, essential: bool, plugin_settings: dict) -> LoadedPlugin:
    """Lee el manifiesto, importa el módulo y valida las funciones de `folder_name`.

    Nunca lanza: cualquier excepción durante el proceso queda en el campo
    `error` del `LoadedPlugin` devuelto.
    """
    folder_path = os.path.join(base_dir, folder_name)
    enabled = _plugin_config(folder_name, plugin_settings).get("enabled", True)

    try:
        manifest_path = os.path.join(folder_path, "plugin.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        manifest = parse_manifest(data, folder_name)

        init_path = os.path.join(folder_path, "__init__.py")
        if not os.path.isfile(init_path):
            raise ValueError("El plugin no tiene un archivo __init__.py en su carpeta.")

        module_name = f"ocr_plugins.{manifest.id}"
        spec = importlib.util.spec_from_file_location(module_name, init_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        for capability, func_name in CAPABILITY_FUNCTIONS.items():
            if capability not in manifest.provides:
                continue
            func = getattr(module, func_name, None)
            if not callable(func):
                raise ValueError(
                    f"El plugin «{manifest.name}» declara la capacidad {capability!r} "
                    f"pero no define la función {func_name!r}."
                )

        return LoadedPlugin(
            id=manifest.id,
            name=manifest.name,
            version=manifest.version,
            provides=list(manifest.provides),
            module=module,
            error=None,
            enabled=enabled,
            essential=essential,
            settings=list(manifest.settings),
        )
    except Exception as exc:
        return LoadedPlugin(
            id=folder_name,
            name=folder_name,
            version="",
            provides=[],
            module=None,
            error=str(exc),
            enabled=enabled,
            essential=essential,
        )


def load_plugins() -> list[LoadedPlugin]:
    """Escanea `plugins_core/` y `plugins/`, carga cada plugin y cachea el resultado."""
    global _plugins_cache

    config = load_config()
    plugin_settings = config.get("plugins", {})

    plugins: list[LoadedPlugin] = []

    for folder_name in _list_subfolders(CORE_PLUGINS_DIR):
        plugins.append(
            _load_plugin_folder(CORE_PLUGINS_DIR, folder_name, essential=True, plugin_settings=plugin_settings)
        )

    for folder_name in _list_subfolders(USER_PLUGINS_DIR):
        if folder_name in ESSENTIAL_PLUGIN_IDS:
            plugins.append(
                LoadedPlugin(
                    id=folder_name,
                    name=folder_name,
                    version="",
                    provides=[],
                    module=None,
                    error=(
                        f"El id «{folder_name}» está reservado para el plugin esencial del "
                        "mismo nombre; este plugin de plugins/ se descarta."
                    ),
                    enabled=_plugin_config(folder_name, plugin_settings).get("enabled", True),
                    essential=False,
                )
            )
            continue
        plugins.append(
            _load_plugin_folder(USER_PLUGINS_DIR, folder_name, essential=False, plugin_settings=plugin_settings)
        )

    _plugins_cache = plugins
    return plugins


def get_plugins() -> list[LoadedPlugin]:
    """Devuelve el cache de plugins, cargándolo la primera vez."""
    if _plugins_cache is None:
        return load_plugins()
    return _plugins_cache


def reload_plugins() -> list[LoadedPlugin]:
    """Descarta el cache y vuelve a escanear e importar todos los plugins."""
    global _plugins_cache
    _plugins_cache = None
    return load_plugins()


def list_providers(capability: str) -> list[LoadedPlugin]:
    """Plugins sin error, habilitados, que declaran `capability`."""
    return [
        plugin
        for plugin in get_plugins()
        if plugin.error is None and plugin.enabled and capability in plugin.provides
    ]


def get_provider(capability: str, plugin_id: str) -> LoadedPlugin | None:
    """El `LoadedPlugin` con `plugin_id` entre los proveedores usables de `capability`."""
    for plugin in list_providers(capability):
        if plugin.id == plugin_id:
            return plugin
    return None


def missing_essentials() -> list[str]:
    """Ids de `ESSENTIAL_PLUGIN_IDS` que no cargaron correctamente."""
    loaded_ids = {plugin.id for plugin in get_plugins() if plugin.error is None}
    return [plugin_id for plugin_id in ESSENTIAL_PLUGIN_IDS if plugin_id not in loaded_ids]


def _selected_reason(capability: str, name: str) -> str:
    return (
        f"{name} es el {_CAPABILITY_NOUN[capability]} seleccionado. "
        f"Elija otro {_CAPABILITY_SHORT_NOUN[capability]} antes de desactivarlo."
    )


def _no_replacement_reason(capability: str, name: str, selected_id: str | None) -> str:
    if selected_id:
        return (
            f"{name} no se puede desactivar: el {_CAPABILITY_NOUN[capability]} "
            f"seleccionado ({selected_id}) no está disponible."
        )
    return f"{name} no se puede desactivar: no hay ningún {_CAPABILITY_NOUN[capability]} seleccionado."


def can_disable(plugin_id: str) -> tuple[bool, str]:
    """Indica si `plugin_id` se puede desactivar y, si no, el motivo en español.

    Un plugin no esencial siempre se puede desactivar. Uno esencial solo si,
    para cada capacidad de `SELECTABLE_CAPABILITIES` que aporta, el
    proveedor seleccionado en `config.json` es otro plugin habilitado y sin
    error.
    """
    plugin = next((p for p in get_plugins() if p.id == plugin_id), None)
    if plugin is None or not plugin.essential:
        return True, ""

    config = load_config()
    selected_by_capability = {
        "ocr": config.get("engine"),
        "translation": config.get("translation_engine"),
    }

    for capability in SELECTABLE_CAPABILITIES:
        if capability not in plugin.provides:
            continue
        selected_id = selected_by_capability[capability]
        if selected_id == plugin_id:
            return False, _selected_reason(capability, plugin.name)
        replacement = get_provider(capability, selected_id) if selected_id else None
        if replacement is None:
            return False, _no_replacement_reason(capability, plugin.name, selected_id)

    return True, ""


def _find_setting_field(plugin_id: str, field_key: str) -> SettingField | None:
    """El `SettingField` con `field_key` en el manifiesto de `plugin_id`, o `None`."""
    plugin = next((p for p in get_plugins() if p.id == plugin_id), None)
    if plugin is None:
        return None
    return next((setting for setting in plugin.settings if setting.key == field_key), None)


def resolve_setting_value(plugin_id: str, field_key: str) -> object:
    """Resuelve el valor actual del campo `field_key` del plugin `plugin_id`.

    Si el campo es de tipo `"api_key"`, lee del keyring del SO bajo el
    username nuevo (`plugin_keyring_username`); si no hay valor guardado ahí
    y se trata de `claude:api_key`, revisa el username legacy
    (`KEYRING_USERNAME`) y, si lo encuentra, lo migra a la ubicación nueva
    (guarda ahí, borra la vieja) antes de devolverlo. Para cualquier otro
    tipo, lee `config["plugins"][plugin_id]["settings"]`, con el `default`
    declarado en el manifiesto como valor de respaldo.
    """
    field_def = _find_setting_field(plugin_id, field_key)
    default = field_def.default if field_def is not None else None

    if field_def is not None and field_def.type == "api_key":
        username = plugin_keyring_username(plugin_id, field_key)
        value = keyring.get_password(KEYRING_SERVICE, username)
        if value is None and plugin_id == "claude" and field_key == "api_key":
            legacy_value = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
            if legacy_value is not None:
                keyring.set_password(KEYRING_SERVICE, username, legacy_value)
                keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
                value = legacy_value
        return value if value is not None else default

    plugin_settings = _plugin_settings(plugin_id)
    return plugin_settings.get(field_key, default)


def save_setting_value(plugin_id: str, field_key: str, value: object) -> None:
    """Persiste el valor nuevo del campo `field_key` del plugin `plugin_id`.

    Mismo despacho que `resolve_setting_value`: `api_key` va al keyring bajo
    el username nuevo; el resto llama a `save_plugin_setting_field`.
    """
    field_def = _find_setting_field(plugin_id, field_key)

    if field_def is not None and field_def.type == "api_key":
        keyring.set_password(KEYRING_SERVICE, plugin_keyring_username(plugin_id, field_key), value)
        return

    save_plugin_setting_field(plugin_id, field_key, value)


def missing_required_settings(plugin_id: str) -> list[SettingField]:
    """`SettingField` requeridos de `plugin_id` cuyo valor resuelto está vacío (`None` o `""`)."""
    plugin = next((p for p in get_plugins() if p.id == plugin_id), None)
    if plugin is None:
        return []

    missing = []
    for setting in plugin.settings:
        if not setting.required:
            continue
        value = resolve_setting_value(plugin_id, setting.key)
        if value is None or value == "":
            missing.append(setting)
    return missing


def set_enabled(plugin_id: str, enabled: bool) -> None:
    """Persiste si `plugin_id` está habilitado y actualiza el cache en memoria.

    No reimporta el módulo del plugin: solo actualiza `enabled` en el
    `LoadedPlugin` cacheado, para que `list_providers`/la vista reflejen el
    cambio sin necesitar `reload_plugins()`.
    """
    save_plugin_enabled(plugin_id, enabled)
    for plugin in get_plugins():
        if plugin.id == plugin_id:
            plugin.enabled = enabled
            break


def _resolved_settings(plugin: LoadedPlugin) -> dict:
    """Diccionario `{field_key: valor}` resolviendo cada campo declarado por `plugin`."""
    return {setting.key: resolve_setting_value(plugin.id, setting.key) for setting in plugin.settings}


def run_ocr(plugin_id: str, image, language_code: str) -> str:
    """Transcribe `image` con el plugin de OCR `plugin_id`.

    Lanza `PluginError` si el proveedor no existe, está deshabilitado o en
    error, o si la propia llamada al plugin lanza (con la excepción
    original disponible en `PluginError.original`).
    """
    provider = get_provider("ocr", plugin_id)
    if provider is None:
        raise PluginError(plugin_id, RuntimeError("no está disponible (deshabilitado, con error o inexistente)."))

    context = PluginContext(plugin_id)
    settings = _resolved_settings(provider)
    try:
        return provider.module.transcribe(image, language_code, settings, context)
    except Exception as exc:
        raise PluginError(provider.name, exc) from exc


def run_translation(plugin_id: str, text: str, source_lang: str, target_lang: str) -> str:
    """Traduce `text` de `source_lang` a `target_lang` con el plugin `plugin_id`.

    Misma semántica de errores que `run_ocr`.
    """
    provider = get_provider("translation", plugin_id)
    if provider is None:
        raise PluginError(plugin_id, RuntimeError("no está disponible (deshabilitado, con error o inexistente)."))

    context = PluginContext(plugin_id)
    settings = _resolved_settings(provider)
    try:
        return provider.module.translate(text, source_lang, target_lang, settings, context)
    except Exception as exc:
        raise PluginError(provider.name, exc) from exc
