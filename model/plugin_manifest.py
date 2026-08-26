"""Parseo y validación del manifiesto `plugin.json` de un plugin.

No importa PySide6 ni conoce `plugin_registry`: solo sabe convertir el
diccionario cargado de `plugin.json` en un `PluginManifest` validado, o
lanzar `ValueError` con un mensaje en español apto para mostrar al usuario.
No importa el módulo del plugin.
"""

from dataclasses import dataclass, field

PLUGIN_API_VERSION = 2

CAPABILITIES = ("ocr", "translation", "preprocessing", "export")

SETTING_FIELD_TYPES = ("text", "number", "boolean", "api_key")

# Qué función debe exponer el módulo del plugin por cada capacidad
# despachable. "export" no aparece: se acepta en el manifiesto pero no se
# valida ni se despacha en esta spec.
CAPABILITY_FUNCTIONS = {
    "ocr": "transcribe",
    "translation": "translate",
    "preprocessing": "preprocess",
}


@dataclass
class SettingField:
    """Un campo de ajuste declarado por un plugin en su manifiesto."""

    key: str
    label: str
    type: str
    required: bool = False
    default: object = None


@dataclass
class PluginManifest:
    """Manifiesto validado de un plugin, leído de su `plugin.json`."""

    id: str
    name: str
    version: str
    api_version: int
    provides: list[str]
    description: str
    settings: list[SettingField] = field(default_factory=list)


def parse_manifest(data: dict, folder_name: str) -> PluginManifest:
    """Valida `data` (el `plugin.json` ya parseado) y devuelve un `PluginManifest`.

    `folder_name` es el nombre de la carpeta donde se encontró el manifiesto;
    debe coincidir con `data["id"]`. Lanza `ValueError` con un mensaje en
    español si falta un campo obligatorio, un tipo es incorrecto, `id` no
    coincide con `folder_name`, `api_version` no es `PLUGIN_API_VERSION` o
    `provides` no es una lista no vacía de capacidades válidas.
    """
    if not isinstance(data, dict):
        raise ValueError("El manifiesto del plugin debe ser un objeto JSON.")

    for field in ("id", "name", "version", "api_version", "provides"):
        if field not in data:
            raise ValueError(f"El manifiesto del plugin no tiene el campo obligatorio {field!r}.")

    plugin_id = data["id"]
    if not isinstance(plugin_id, str) or not plugin_id:
        raise ValueError("El campo 'id' del manifiesto debe ser un texto no vacío.")
    if plugin_id != folder_name:
        raise ValueError(
            f"El 'id' del manifiesto ({plugin_id!r}) debe coincidir con el nombre "
            f"de la carpeta ({folder_name!r})."
        )

    name = data["name"]
    if not isinstance(name, str) or not name:
        raise ValueError("El campo 'name' del manifiesto debe ser un texto no vacío.")

    version = data["version"]
    if not isinstance(version, str) or not version:
        raise ValueError("El campo 'version' del manifiesto debe ser un texto no vacío.")

    api_version = data["api_version"]
    if not isinstance(api_version, int) or isinstance(api_version, bool):
        raise ValueError("El campo 'api_version' del manifiesto debe ser un entero.")
    if api_version != PLUGIN_API_VERSION:
        raise ValueError(
            f"El plugin {plugin_id!r} usa api_version {api_version}, pero esta "
            f"aplicación solo admite api_version {PLUGIN_API_VERSION}."
        )

    provides = data["provides"]
    if not isinstance(provides, list) or not provides:
        raise ValueError("El campo 'provides' del manifiesto debe ser una lista no vacía.")
    for capability in provides:
        if capability not in CAPABILITIES:
            raise ValueError(
                f"El plugin {plugin_id!r} declara la capacidad {capability!r}, "
                f"que no es una capacidad válida ({', '.join(CAPABILITIES)})."
            )

    description = data.get("description", "")
    if not isinstance(description, str):
        raise ValueError("El campo 'description' del manifiesto debe ser un texto.")

    settings = _parse_settings(data.get("settings", []), plugin_id)

    return PluginManifest(
        id=plugin_id,
        name=name,
        version=version,
        api_version=api_version,
        provides=list(provides),
        description=description,
        settings=settings,
    )


def _parse_settings(raw_settings: object, plugin_id: str) -> list[SettingField]:
    """Valida el campo `settings` del manifiesto y devuelve sus `SettingField`.

    `raw_settings` es el valor crudo de `data.get("settings", [])`. Lanza
    `ValueError` con un mensaje en español si no es una lista, si a algún
    elemento le falta `key`/`label`/`type`, si `type` no es uno de
    `SETTING_FIELD_TYPES`, o si hay `key` repetidas dentro del mismo plugin.
    """
    if not isinstance(raw_settings, list):
        raise ValueError(f"El campo 'settings' del plugin {plugin_id!r} debe ser una lista.")

    fields: list[SettingField] = []
    seen_keys: set[str] = set()
    for item in raw_settings:
        if not isinstance(item, dict):
            raise ValueError(
                f"Cada elemento de 'settings' del plugin {plugin_id!r} debe ser un objeto JSON."
            )

        for required_field in ("key", "label", "type"):
            if required_field not in item:
                raise ValueError(
                    f"Un campo de 'settings' del plugin {plugin_id!r} no tiene "
                    f"el campo obligatorio {required_field!r}."
                )

        key = item["key"]
        if not isinstance(key, str) or not key:
            raise ValueError(
                f"El campo 'key' de un ajuste del plugin {plugin_id!r} debe ser un texto no vacío."
            )
        if key in seen_keys:
            raise ValueError(
                f"El plugin {plugin_id!r} declara la clave de ajuste {key!r} más de una vez."
            )
        seen_keys.add(key)

        label = item["label"]
        if not isinstance(label, str) or not label:
            raise ValueError(
                f"El campo 'label' del ajuste {key!r} del plugin {plugin_id!r} debe ser "
                "un texto no vacío."
            )

        field_type = item["type"]
        if field_type not in SETTING_FIELD_TYPES:
            raise ValueError(
                f"El ajuste {key!r} del plugin {plugin_id!r} declara el tipo {field_type!r}, "
                f"que no es válido ({', '.join(SETTING_FIELD_TYPES)})."
            )

        required = item.get("required", False)
        if not isinstance(required, bool):
            raise ValueError(
                f"El campo 'required' del ajuste {key!r} del plugin {plugin_id!r} debe ser booleano."
            )

        fields.append(
            SettingField(
                key=key,
                label=label,
                type=field_type,
                required=required,
                default=item.get("default"),
            )
        )

    return fields
