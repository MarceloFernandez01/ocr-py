"""Transcripción de texto en imágenes mediante Tesseract OCR."""

import pytesseract
from PIL import Image
from pytesseract import Output

from model.image_preprocessing import generate_variants
from model.image_tiling import prepare_tiles_from_image


def transcribe_cropped_image(
    image: Image.Image,
    language_code: str,
    tesseract_path: str | None,
    min_word_confidence: int = 0,
) -> str:
    """Transcribe una `PIL.Image` ya recortada en memoria.

    Aplica `prepare_tiles_from_image` para partirla en tiles si hace falta y
    `transcribe_image_variants` por tile, concatenando los resultados en
    orden, separados por salto de línea.

    Args:
        image: imagen ya recortada a transcribir.
        language_code: código de idioma de Tesseract (`spa`, `eng` o `spa+eng`).
        tesseract_path: ruta al ejecutable de Tesseract, o None si ya está en el PATH.
        min_word_confidence: confianza mínima (0-100) para conservar una palabra
            en el texto final; `0` no filtra nada.

    Devuelve el texto reconocido.
    """
    if tesseract_path is not None:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    tiles = prepare_tiles_from_image(image)
    texts = [
        transcribe_image_variants(tile, language_code, None, min_word_confidence) for tile in tiles
    ]
    return "\n".join(texts)


def _build_text_from_data(data: dict, min_word_confidence: int) -> str:
    """Reconstruye el texto de `image_to_data`, agrupado por línea, descartando ruido.

    Descarta las entradas sin texto y las palabras con `conf < min_word_confidence`,
    y une las palabras restantes preservando el agrupamiento por línea que ya
    reporta Tesseract (`data["block_num"]`/`data["line_num"]`), en el orden en que
    aparecen.
    """
    lines: dict[tuple[int, int], list[str]] = {}
    line_order: list[tuple[int, int]] = []

    for conf, text, block_num, line_num in zip(
        data["conf"], data["text"], data["block_num"], data["line_num"]
    ):
        if not text.strip() or float(conf) < min_word_confidence:
            continue

        key = (block_num, line_num)
        if key not in lines:
            lines[key] = []
            line_order.append(key)
        lines[key].append(text)

    return "\n".join(" ".join(lines[key]) for key in line_order)


def transcribe_image_variants(
    image: Image.Image,
    language_code: str,
    tesseract_path: str | None,
    min_word_confidence: int = 0,
    variants: list[tuple[str, Image.Image]] | None = None,
) -> str:
    """Transcribe una `PIL.Image` ya en memoria (sin ruta de archivo ni tiling).

    Puntúa cada variante por confianza media de palabra (`conf >= 0`, texto
    no vacío) y reconstruye el texto de la de mayor confianza a partir de
    `image_to_data`, descartando las palabras con `conf < min_word_confidence`;
    empate o todas vacías → gana la variante `original`. Misma lógica que usa
    internamente `transcribe_large_image`, expuesta aquí para el flujo de
    captura de pantalla en vivo.

    Args:
        image: imagen ya cargada en memoria a transcribir.
        language_code: código de idioma de Tesseract (`spa`, `eng` o `spa+eng`).
        tesseract_path: ruta al ejecutable de Tesseract, o None si ya está en el PATH.
        min_word_confidence: confianza mínima (0-100) para conservar una palabra
            en el texto final; `0` no filtra nada (comportamiento sin regresión).
        variants: lista de `(nombre, imagen)` a evaluar; con `None` se generan
            internamente con `generate_variants(image)` (sin regresión).
    """
    if tesseract_path is not None:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    tesseract_config = "-c tessedit_char_blacklist=|"
    if variants is None:
        variants = generate_variants(image)
    best_variant = variants[0][1]  # original, por si todas las variantes empatan o quedan vacías
    best_data = None
    best_confidence = -1.0

    for _, variant in variants:
        data = pytesseract.image_to_data(
            variant, lang=language_code, output_type=Output.DICT, config=tesseract_config
        )
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
            best_data = data

    if best_data is None:
        best_data = pytesseract.image_to_data(
            best_variant, lang=language_code, output_type=Output.DICT, config=tesseract_config
        )

    return _build_text_from_data(best_data, min_word_confidence)
