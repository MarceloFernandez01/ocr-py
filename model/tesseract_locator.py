"""Localización del ejecutable de Tesseract OCR en el sistema."""

import os
import shutil
import sys

from model.config_model import load_config


def resolve_tesseract_path() -> str | None:
    """Resuelve la ruta del ejecutable de Tesseract.

    Si la app corre empaquetada (PyInstaller), usa el Tesseract embebido
    junto al ejecutable. Si no, intenta encontrarlo en el PATH del sistema;
    si no está, revisa la ruta guardada en `plugins.tesseract.settings.tesseract_path`
    de config.json (descartándola si ya no existe en disco).

    Devuelve la ruta encontrada, o None si no se pudo resolver.
    """
    bundled_path = _resolve_bundled_path()
    if bundled_path:
        return bundled_path

    path_from_system = shutil.which("tesseract")
    if path_from_system:
        return path_from_system

    config = load_config()
    saved_path = config.get("plugins", {}).get("tesseract", {}).get("settings", {}).get("tesseract_path")
    if saved_path and os.path.exists(saved_path):
        return saved_path

    return None


def _resolve_bundled_path() -> str | None:
    """Devuelve la ruta del Tesseract embebido si la app corre congelada.

    También fija TESSDATA_PREFIX apuntando a la carpeta tessdata embebida,
    para evitar que una variable de entorno preexistente en la máquina del
    usuario apunte a otra instalación de Tesseract.
    """
    if not getattr(sys, "frozen", False):
        return None

    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    tesseract_dir = os.path.join(base_dir, "tesseract")
    tesseract_exe = os.path.join(tesseract_dir, "tesseract.exe")
    if not os.path.exists(tesseract_exe):
        return None

    os.environ["TESSDATA_PREFIX"] = os.path.join(tesseract_dir, "tessdata")
    return tesseract_exe
