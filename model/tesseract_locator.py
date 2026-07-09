"""Localización del ejecutable de Tesseract OCR en el sistema."""

import os
import shutil

from model.config_model import load_config


def resolve_tesseract_path() -> str | None:
    """Resuelve la ruta del ejecutable de Tesseract.

    Intenta primero encontrarlo en el PATH del sistema. Si no está,
    revisa la ruta guardada en config.json; si esa ruta ya no existe
    en disco, se descarta.

    Devuelve la ruta encontrada, o None si no se pudo resolver.
    """
    path_from_system = shutil.which("tesseract")
    if path_from_system:
        return path_from_system

    config = load_config()
    saved_path = config.get("tesseract_path")
    if saved_path and os.path.exists(saved_path):
        return saved_path

    return None
