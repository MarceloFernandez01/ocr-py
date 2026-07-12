"""Lectura y escritura de la configuración persistida en config.json."""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


def load_config() -> dict:
    """Carga la configuración desde config.json.

    Devuelve un diccionario con los valores default (`theme` en `"dark"`) si el
    archivo no existe o no incluye alguna clave.
    """
    if not os.path.exists(CONFIG_PATH):
        config = {}
    else:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    config.setdefault("theme", "dark")
    return config


def save_tesseract_path(path: str) -> None:
    """Guarda la ruta del ejecutable de Tesseract en config.json.

    Args:
        path: ruta absoluta al ejecutable tesseract.exe.
    """
    config = load_config()
    config["tesseract_path"] = path
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
