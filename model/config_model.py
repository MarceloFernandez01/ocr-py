"""Lectura y escritura de la configuración persistida en config.json."""

import json
import os
import sys
from datetime import datetime

if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(_BASE_DIR, "config.json")

KEYRING_SERVICE = "ocr-py"
KEYRING_USERNAME = "anthropic_api_key"


def load_config() -> dict:
    """Carga la configuración desde config.json.

    Devuelve un diccionario con los valores default (`theme` en `"dark"`,
    `engine` en `"tesseract"`, `min_word_confidence` en `95`) si el archivo no
    existe o no incluye alguna clave.
    """
    if not os.path.exists(CONFIG_PATH):
        config = {}
    else:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    config.setdefault("theme", "dark")
    config.setdefault("engine", "tesseract")
    config.setdefault("min_word_confidence", 95)
    config.setdefault("live_claude_enabled", False)
    config.setdefault("text_similarity_threshold", 90)
    config.setdefault("pixel_change_sensitivity", 2)
    config.setdefault("claude_cooldown_seconds", 10)
    config.setdefault("claude_monthly_budget_usd", 5.0)
    config.setdefault(
        "claude_spend",
        {"month": datetime.now().strftime("%Y-%m"), "usd": 0.0, "calls": 0},
    )
    config.setdefault("hotkey_toggle", "Ctrl+Shift+P")
    config.setdefault("hotkey_close", "Ctrl+Shift+Q")
    config.setdefault("translation_engine", "argos")
    config.setdefault("plugins", {})

    if _migrate_legacy_tesseract_path(config):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    return config


def _migrate_legacy_tesseract_path(config: dict) -> bool:
    """Mueve la clave legacy top-level `tesseract_path` a
    `plugins.tesseract.settings.tesseract_path`, si existe.

    Devuelve True si se realizó la migración, para que `load_config()` sepa
    si debe reescribir config.json.
    """
    if "tesseract_path" not in config:
        return False
    path = config.pop("tesseract_path")
    plugins = config.setdefault("plugins", {})
    entry = plugins.setdefault("tesseract", {"enabled": True, "settings": {}})
    entry.setdefault("settings", {})
    entry["settings"]["tesseract_path"] = path
    return True


def save_theme(theme: str) -> None:
    """Persiste el tema elegido en config.json, preservando el resto de claves.

    Args:
        theme: "dark" o "light".
    """
    config = load_config()
    config["theme"] = theme
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_engine(engine: str) -> None:
    """Persiste el motor OCR elegido en config.json, preservando el resto de claves.

    Args:
        engine: "tesseract" o "claude".
    """
    config = load_config()
    config["engine"] = engine
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_min_word_confidence(value: int) -> None:
    """Persiste el umbral de confianza mínima por palabra en config.json.

    Args:
        value: entero 0-100. Palabras con confianza por debajo de este valor
            se descartan del texto final de Tesseract; `0` desactiva el filtro.
    """
    config = load_config()
    config["min_word_confidence"] = value
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_live_claude_enabled(value: bool) -> None:
    """Persiste si Claude está habilitado como motor de OCR en vivo.

    Args:
        value: solo tiene efecto si `engine` es `"claude"`; con `False`, OCR
            en vivo usa Tesseract sin importar el motor configurado.
    """
    config = load_config()
    config["live_claude_enabled"] = value
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_text_similarity_threshold(value: int) -> None:
    """Persiste el umbral de similitud de texto usado en OCR en vivo.

    Args:
        value: entero 0-100. Dos textos se consideran iguales si su similitud
            es mayor o igual a este valor; `0` desactiva el filtro.
    """
    config = load_config()
    config["text_similarity_threshold"] = value
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_pixel_change_sensitivity(value: int) -> None:
    """Persiste la sensibilidad del diff de píxeles en OCR en vivo.

    Args:
        value: entero 0-100, en centésimas de diferencia media de píxeles.
    """
    config = load_config()
    config["pixel_change_sensitivity"] = value
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_claude_cooldown_seconds(value: int) -> None:
    """Persiste el tiempo mínimo entre llamadas a Claude en OCR en vivo.

    Args:
        value: entero 1-120, en segundos.
    """
    config = load_config()
    config["claude_cooldown_seconds"] = value
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_claude_monthly_budget_usd(value: float) -> None:
    """Persiste el presupuesto mensual de referencia para el medidor de gasto.

    Args:
        value: monto en USD. Solo informa, no bloquea llamadas.
    """
    config = load_config()
    config["claude_monthly_budget_usd"] = value
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_claude_spend(value: dict) -> None:
    """Persiste el acumulador de gasto mensual de Claude en config.json.

    Args:
        value: diccionario con `month` (`"YYYY-MM"`), `usd` y `calls`.
    """
    config = load_config()
    config["claude_spend"] = value
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_hotkey_toggle(value: str) -> None:
    """Persiste el atajo global de pausar/reanudar en config.json.

    Args:
        value: combinación en notación `QKeySequence` (ej. `"Ctrl+Shift+P"`).
    """
    config = load_config()
    config["hotkey_toggle"] = value
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_hotkey_close(value: str) -> None:
    """Persiste el atajo global de cerrar el overlay en config.json.

    Args:
        value: combinación en notación `QKeySequence` (ej. `"Ctrl+Shift+Q"`).
    """
    config = load_config()
    config["hotkey_close"] = value
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_translation_engine(value: str) -> None:
    """Persiste el plugin de traducción elegido en config.json.

    Args:
        value: id del plugin de traducción activo (ej. `"argos"`).
    """
    config = load_config()
    config["translation_engine"] = value
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_plugin_enabled(plugin_id: str, enabled: bool) -> None:
    """Persiste si el plugin `plugin_id` está habilitado en config.json.

    Args:
        plugin_id: id del plugin, tal como figura en su `plugin.json`.
        enabled: `True` para habilitarlo, `False` para deshabilitarlo.
    """
    config = load_config()
    plugins = config.setdefault("plugins", {})
    entry = plugins.setdefault(plugin_id, {"enabled": True, "settings": {}})
    entry["enabled"] = enabled
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_plugin_settings(plugin_id: str, settings: dict) -> None:
    """Persiste los ajustes propios del plugin `plugin_id` en config.json.

    Args:
        plugin_id: id del plugin, tal como figura en su `plugin.json`.
        settings: diccionario de ajustes específico del plugin.
    """
    config = load_config()
    plugins = config.setdefault("plugins", {})
    entry = plugins.setdefault(plugin_id, {"enabled": True, "settings": {}})
    entry["settings"] = settings
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_plugin_setting_field(plugin_id: str, key: str, value: object) -> None:
    """Persiste un único campo de ajuste del plugin `plugin_id` en config.json.

    Preserva el resto de campos de `settings` y el valor de `enabled`.

    Args:
        plugin_id: id del plugin, tal como figura en su `plugin.json`.
        key: clave del campo dentro de `settings` (el `key` del `SettingField`).
        value: valor nuevo para ese campo.
    """
    config = load_config()
    plugins = config.setdefault("plugins", {})
    entry = plugins.setdefault(plugin_id, {"enabled": True, "settings": {}})
    entry.setdefault("settings", {})
    entry["settings"][key] = value
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def plugin_keyring_username(plugin_id: str, field_key: str) -> str:
    """Username bajo el que se guarda en el keyring del SO un campo `api_key`
    de un plugin, con el formato `"<plugin_id>:<field_key>"`.
    """
    return f"{plugin_id}:{field_key}"
