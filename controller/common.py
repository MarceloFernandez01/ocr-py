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
