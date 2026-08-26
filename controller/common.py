"""Utilidades compartidas entre `OcrController` y `LiveOcrController`."""

import time

from PySide6.QtWidgets import QInputDialog, QLineEdit, QWidget

from model.plugin_registry import missing_required_settings, save_setting_value

COUNTER_INTERVAL_MS = 200

LANGUAGE_MAP = {
    "Español": "spa",
    "Inglés": "eng",
    "Ambos": "spa+eng",
}


def prompt_missing_settings(parent: QWidget, plugin_id: str) -> bool:
    """Pide, por cada ajuste obligatorio faltante de `plugin_id`, su valor vía
    un diálogo genérico (`QInputDialog.getText`, oculto para campos `api_key`)
    y lo persiste con `save_setting_value`.

    Devuelve False sin persistir nada si el usuario cancela o deja vacío
    cualquiera de los diálogos; True si todos los ajustes obligatorios ya
    estaban resueltos o se completaron.
    """
    for field in missing_required_settings(plugin_id):
        value, ok = QInputDialog.getText(
            parent,
            field.label,
            field.label,
            echo=QLineEdit.Password if field.type == "api_key" else QLineEdit.Normal,
        )
        if not ok or not value:
            return False
        save_setting_value(plugin_id, field.key, value)
    return True


def processing_label(start: float) -> str:
    """Devuelve el texto "Procesando... Ns" según los segundos transcurridos desde `start`."""
    elapsed = int(time.monotonic() - start)
    return f"Procesando... {elapsed}s"
