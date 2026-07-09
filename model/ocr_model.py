"""Transcripción de texto en imágenes mediante Tesseract OCR."""

import pytesseract


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
