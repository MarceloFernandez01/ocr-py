"""Lectura y escritura de la configuración persistida en config.json."""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


def load_config() -> dict:
    """Carga la configuración desde config.json.

    Devuelve un diccionario vacío si el archivo no existe.
    """
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tesseract_path(path: str) -> None:
    """Guarda la ruta del ejecutable de Tesseract en config.json.

    Args:
        path: ruta absoluta al ejecutable tesseract.exe.
    """
    config = load_config()
    config["tesseract_path"] = path
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
