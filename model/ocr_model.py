"""Transcripción de texto en imágenes mediante Tesseract OCR."""

import pytesseract
from PIL import Image
from pytesseract import Output

from model.image_preprocessing import generate_variants
from model.image_tiling import prepare_tiles


def transcribe(image_path: str, language_code: str, tesseract_path: str | None) -> str:
    """Transcribe el texto de la imagen ubicada en `image_path`.

    Args:
        image_path: ruta a la imagen a transcribir.
        language_code: código de idioma de Tesseract (`spa`, `eng` o `spa+eng`).
        tesseract_path: ruta al ejecutable de Tesseract, o None si ya está en el PATH.

    Devuelve el texto reconocido.
    """
    if tesseract_path is not None:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    return pytesseract.image_to_string(image_path, lang=language_code)


def transcribe_large_image(image_path: str, language_code: str, tesseract_path: str | None) -> str:
    """Transcribe imágenes grandes o de relación de aspecto extrema partiéndolas en tiles.

    Aplica `prepare_tiles` para obtener downscale y/o tiling según haga falta,
    transcribe cada tile por separado con Tesseract y concatena los resultados
    en orden, separados por salto de línea, sin deduplicar el texto solapado.

    Args:
        image_path: ruta a la imagen a transcribir.
        language_code: código de idioma de Tesseract (`spa`, `eng` o `spa+eng`).
        tesseract_path: ruta al ejecutable de Tesseract, o None si ya está en el PATH.

    Devuelve el texto reconocido.
    """
    if tesseract_path is not None:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    tiles = prepare_tiles(image_path)
    texts = [transcribe_image_variants(tile, language_code, None) for tile in tiles]
    return "\n".join(texts)


def transcribe_image_variants(image: Image.Image, language_code: str, tesseract_path: str | None) -> str:
    """Transcribe una `PIL.Image` ya en memoria (sin ruta de archivo ni tiling).

    Genera las variantes preprocesadas de `image`, puntúa cada una por confianza
    media de palabra (`conf >= 0`, texto no vacío) y devuelve el texto de la de
    mayor confianza; empate o todas vacías → gana la variante `original`. Misma
    lógica que usa internamente `transcribe_large_image`, expuesta aquí para el
    flujo de captura de pantalla en vivo.

    Args:
        image: imagen ya cargada en memoria a transcribir.
        language_code: código de idioma de Tesseract (`spa`, `eng` o `spa+eng`).
        tesseract_path: ruta al ejecutable de Tesseract, o None si ya está en el PATH.
    """
    if tesseract_path is not None:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    variants = generate_variants(image)
    best_variant = variants[0][1]  # original, por si todas las variantes empatan o quedan vacías
    best_confidence = -1.0

    for _, variant in variants:
        data = pytesseract.image_to_data(variant, lang=language_code, output_type=Output.DICT)
        confidences = [
            float(conf)
            for conf, text in zip(data["conf"], data["text"])
            if float(conf) >= 0 and text.strip()
        ]
        if not confidences:
            continue

        confidence = sum(confidences) / len(confidences)
        if confidence > best_confidence:
            best_confidence = confidence
            best_variant = variant

    return pytesseract.image_to_string(best_variant, lang=language_code)
