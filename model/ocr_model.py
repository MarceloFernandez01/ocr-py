"""Transcripción de texto en imágenes mediante Tesseract OCR."""

import pytesseract

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
    texts = [pytesseract.image_to_string(tile, lang=language_code) for tile in tiles]
    return "\n".join(texts)
