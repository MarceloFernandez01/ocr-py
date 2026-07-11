"""Generación de variantes preprocesadas de una imagen para mejorar el OCR sobre fondos complejos."""

import cv2
import numpy as np
from PIL import Image, ImageOps

MIN_TEXT_HEIGHT = 150  # px, alto mínimo antes de escalar la imagen
MAX_UPSCALE = 4        # tope de factor de escala


def generate_variants(image: Image.Image) -> list[tuple[str, Image.Image]]:
    """Devuelve el conjunto fijo de variantes preprocesadas de `image`.

    Si `image` tiene menos de `MIN_TEXT_HEIGHT` píxeles de alto (típico de capturas
    de una sola línea), se escala primero (hasta `MAX_UPSCALE` veces) para que
    Tesseract pueda resolver texto con contorno grueso o fuentes decorativas.

    El primer elemento siempre es ("original", image) para garantizar no-regresión
    (`image` ya escalada si hizo falta). El resto aplica escala de grises,
    autocontraste, Otsu (directo e invertido), umbral adaptativo y separación por
    canal de color, usando cv2/numpy. No importa Tkinter ni pytesseract (respeta MVC).
    """
    image = _upscale_if_needed(image)
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


def _upscale_if_needed(image: Image.Image) -> Image.Image:
    """Escala `image` si su alto es menor a `MIN_TEXT_HEIGHT`, hasta `MAX_UPSCALE`
    veces, preservando la relación de aspecto.
    """
    width, height = image.size
    if height >= MIN_TEXT_HEIGHT:
        return image

    scale = min(MIN_TEXT_HEIGHT / height, MAX_UPSCALE)
    new_size = (round(width * scale), round(height * scale))
    return image.resize(new_size, Image.LANCZOS)


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
