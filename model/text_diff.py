"""Comparación de similitud entre dos transcripciones de texto.

Se usa en OCR en vivo para distinguir un cambio real de texto de ruido visual
(cursor parpadeante, animaciones, jitter de Tesseract entre capturas casi
idénticas). No importa PySide6: es lógica de modelo pura.
"""

import re
from difflib import SequenceMatcher


def normalize_text(text: str) -> str:
    """Colapsa espacios y saltos de línea repetidos y recorta bordes.

    Evita que diferencias de espaciado entre dos transcripciones del mismo
    contenido se cuenten como un cambio real.
    """
    return re.sub(r"\s+", " ", text).strip()


def has_text_changed(previous: str | None, current: str, threshold: int) -> bool:
    """Indica si `current` representa un cambio de texto respecto de `previous`.

    `previous is None` siempre devuelve `True` (no hay referencia previa).
    `threshold == 0` siempre devuelve `True` (filtro desactivado). En el resto
    de los casos, compara la similitud normalizada (0-100) entre ambos textos
    contra `threshold`: por debajo del umbral se considera cambio.
    """
    if previous is None:
        return True
    if threshold == 0:
        return True

    ratio = SequenceMatcher(None, normalize_text(previous), normalize_text(current)).ratio() * 100
    return ratio < threshold
