"""Comparación de imágenes para detectar cambios significativos entre capturas."""

import numpy as np
from PIL import Image

CHANGE_THRESHOLD = 0.02  # diferencia media de píxeles (0-255) a partir de la cual se considera cambio


def has_changed(previous: Image.Image | None, current: Image.Image, threshold: float = CHANGE_THRESHOLD) -> bool:
    """Determina si `current` difiere significativamente de `previous`.

    Normaliza ambas imágenes a escala de grises y al mismo tamaño (el de `current`)
    antes de calcular la diferencia absoluta media de píxeles. `previous=None`
    (primera captura) siempre devuelve `True`. No importa PySide6 ni pytesseract.
    """
    if previous is None:
        return True

    current_gray = np.array(current.convert("L"))
    previous_gray = np.array(previous.convert("L").resize(current.size))

    diff = np.abs(current_gray.astype(np.int16) - previous_gray.astype(np.int16))
    return diff.mean() > threshold
