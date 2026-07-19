"""OCR alternativo vía Claude Haiku 4.5 (SDK oficial `anthropic`).

El import del SDK es perezoso (dentro de la función) para no pagar su costo
de import en cada arranque de la app cuando el motor Claude no está
seleccionado, mismo patrón que `model/translation_model.py`.
"""

import base64
import io

from PIL import Image

MODEL_NAME = "claude-haiku-4-5-20251001"

MAX_IMAGE_DIMENSION_PX = 8000
"""Límite de lado más largo de imagen aceptado por la API de Anthropic."""

MAX_IMAGE_BYTES = 5 * 1024 * 1024
"""Límite de tamaño de imagen (bytes) aceptado por la API de Anthropic."""

LANGUAGE_INSTRUCTIONS = {
    "spa": "El texto en la imagen está en español.",
    "eng": "El texto en la imagen está en inglés.",
    "spa+eng": "El texto en la imagen puede estar en español, en inglés, o mezclar ambos idiomas.",
}
"""Mapea los códigos internos de idioma (los mismos que usa `model/ocr_model.py`
para Tesseract: `spa`/`eng`/`spa+eng`) a la instrucción de idioma del prompt."""


def _resize_if_needed(image: Image.Image) -> Image.Image:
    """Redimensiona `image` solo si excede el límite de dimensión de la API de Anthropic.
    No reimplementa tiling ni preprocesamiento 
    — solo evita el error de la API cuando la imagen supera ese límite.
    """
    width, height = image.size
    longest_side = max(width, height)
    if longest_side <= MAX_IMAGE_DIMENSION_PX:
        return image

    scale = MAX_IMAGE_DIMENSION_PX / longest_side
    new_size = (round(width * scale), round(height * scale))
    return image.resize(new_size, Image.LANCZOS)


def _encode_image(image: Image.Image) -> tuple[str, str]:
    """Codifica `image` a base64, bajando a JPEG si el PNG excede el límite de bytes de la API.

    Devuelve una tupla `(media_type, base64_data)`.
    """
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    if buffer.tell() <= MAX_IMAGE_BYTES:
        return "image/png", base64.b64encode(buffer.getvalue()).decode("ascii")

    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=85)
    return "image/jpeg", base64.b64encode(buffer.getvalue()).decode("ascii")


def transcribe_image_claude(image: Image.Image, language_code: str, api_key: str) -> str:
    """Transcribe `image` a texto vía Claude Haiku 4.5.

    Envía la imagen completa a la API de Anthropic (sin tiling ni
    preprocesamiento propio de Tesseract), redimensionándola antes solo si
    excede los límites de tamaño de la API. Incluye en el prompt una
    instrucción de idioma derivada de `language_code` (`"spa"`, `"eng"` o
    `"spa+eng"`, mismos códigos que usa Tesseract).

    Las excepciones propias del SDK `anthropic` (`AuthenticationError`,
    `APIConnectionError`, `RateLimitError`, etc.) se dejan propagar; quien
    llama a esta función es responsable de capturarlas.

    Devuelve el texto reconocido.
    """
    import anthropic

    resized_image = _resize_if_needed(image)
    media_type, image_data = _encode_image(resized_image)

    prompt = (
        "Transcribe todo el texto visible en esta imagen exactamente como aparece, "
        "preservando saltos de línea y el orden de lectura natural. "
        f"{LANGUAGE_INSTRUCTIONS[language_code]} "
        "Devuelve únicamente el texto transcripto, sin comentarios ni explicaciones adicionales."
    )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    return response.content[0].text
