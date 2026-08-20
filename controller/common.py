"""Utilidades compartidas entre `OcrController` y `LiveOcrController`."""

import os
import time

from PySide6.QtWidgets import QFileDialog, QWidget

from model.config_model import save_tesseract_path

COUNTER_INTERVAL_MS = 200

LANGUAGE_MAP = {
    "Español": "spa",
    "Inglés": "eng",
    "Ambos": "spa+eng",
}

KEYRING_SERVICE = "ocr-py"
KEYRING_USERNAME = "anthropic_api_key"


def prompt_tesseract_path(parent: QWidget) -> str | None:
    """Pide al usuario la ruta del ejecutable de Tesseract y la persiste si es válida."""
    path, _ = QFileDialog.getOpenFileName(
        parent,
        "Ubicar tesseract.exe",
        filter="Ejecutables (*.exe)",
    )
    if not path or not os.path.exists(path):
        return None

    save_tesseract_path(path)
    return path


def processing_label(start: float) -> str:
    """Devuelve el texto "Procesando... Ns" según los segundos transcurridos desde `start`."""
    elapsed = int(time.monotonic() - start)
    return f"Procesando... {elapsed}s"


def format_claude_error(error: Exception) -> str:
    """Traduce una excepción del SDK `anthropic` a un mensaje legible en español.

    Import perezoso de `anthropic` (mismo patrón que `model/claude_ocr_model.py`):
    esta función solo se llama tras una transcripción fallida con el motor Claude.
    """
    import anthropic

    if isinstance(error, anthropic.AuthenticationError):
        return "La API key de Anthropic no es válida. Por favor cambierla desde Configuración."
    if isinstance(error, anthropic.APIConnectionError):
        return "No se pudo conectar con la API de Anthropic. Por favor revise la conexión a internet."
    if isinstance(error, anthropic.RateLimitError):
        return "Se alcanzó el límite de uso (rate limit) de la API de Anthropic. Espere unos minutos y vuelva a intentar."
    if isinstance(error, anthropic.APIStatusError):
        detail = error.message
        if isinstance(error.body, dict):
            detail = error.body.get("error", {}).get("message", detail)
        return f"La API de Anthropic devolvió un error ({error.status_code}): {detail}"
    return str(error)
