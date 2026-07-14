"""Utilidades compartidas para las pruebas de integración de OCR y traducción."""

import re

import pytest
from PIL import Image, ImageDraw, ImageFont

from model.tesseract_locator import resolve_tesseract_path

FONT_PATH = "C:/Windows/Fonts/arial.ttf"


def require_tesseract() -> str:
    """Salta el test si no se puede resolver una ruta de Tesseract instalada."""
    tesseract_path = resolve_tesseract_path()
    if tesseract_path is None:
        pytest.skip("Tesseract no está instalado o no se pudo localizar")
    return tesseract_path


def make_text_image(text: str, size: int = 64) -> Image.Image:
    """Genera una imagen blanca con `text` dibujado en negro, apta para OCR."""
    font = ImageFont.truetype(FONT_PATH, size)
    dummy = Image.new("RGB", (1, 1))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    padding = size
    width = (bbox[2] - bbox[0]) + padding * 2
    height = (bbox[3] - bbox[1]) + padding * 2

    image = Image.new("RGB", (width, height), color="white")
    ImageDraw.Draw(image).text((padding, padding), text, font=font, fill="black")
    return image


def normalizar(texto: str) -> str:
    """Minúsculas + colapso de espacios/saltos de línea, para aserciones robustas."""
    return re.sub(r"\s+", " ", texto).strip().lower()
