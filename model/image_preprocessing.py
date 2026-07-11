"""Generación de variantes preprocesadas de una imagen para mejorar el OCR sobre fondos complejos."""

import cv2
import numpy as np
from PIL import Image, ImageOps


def generate_variants(image: Image.Image) -> list[tuple[str, Image.Image]]:
    """Devuelve el conjunto fijo de variantes preprocesadas de `image`.

    El primer elemento siempre es ("original", image) para garantizar no-regresión.
    El resto aplica escala de grises, autocontraste, Otsu (directo e invertido),
    umbral adaptativo y separación por canal de color, usando cv2/numpy.
    No importa Tkinter ni pytesseract (respeta MVC).
    """
    gray = np.array(ImageOps.autocontrast(image.convert("L")))
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, otsu_invertido = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    adaptativo = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )
    canal_color = _mejor_canal_color(image)

    return [
        ("original", image),
        ("gris_autocontraste", Image.fromarray(gray)),
        ("otsu", Image.fromarray(otsu)),
        ("otsu_invertido", Image.fromarray(otsu_invertido)),
        ("adaptativo", Image.fromarray(adaptativo)),
        ("canal_color", canal_color),
    ]


def _mejor_canal_color(image: Image.Image) -> Image.Image:
    """Separa el texto del fondo usando el canal RGB de mayor varianza + Otsu.

    Útil cuando el texto y el fondo tienen colores distintos pero luminosidad
    similar (ej. texto naranja sobre fondo violeta), donde la escala de grises
    los mezcla en un tono parecido.
    """
    rgb = np.array(image.convert("RGB"))
    canal = max(range(3), key=lambda i: rgb[:, :, i].var())
    _, binarizado = cv2.threshold(
        rgb[:, :, canal], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return Image.fromarray(binarizado)
