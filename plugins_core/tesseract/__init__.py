"""Plugin esencial: motor de OCR local vía Tesseract (`pytesseract`).

Envoltorio fino sobre `model/tesseract_locator.py`, `model/image_tiling.py`
y `model/ocr_model.py`; la lógica de esas specs no se mueve ni se reescribe.
"""

from PIL import Image

from model.config_model import load_config
from model.image_tiling import prepare_tiles_from_image
from model.ocr_model import transcribe_image_variants
from model.tesseract_locator import resolve_tesseract_path


def transcribe(image: Image.Image, language_code: str, settings: dict, context) -> str:
    """Transcribe `image` con Tesseract, partiéndola en tiles y usando el preprocesamiento de `context`.

    Args:
        image: imagen ya cargada en memoria a transcribir.
        language_code: código de idioma de Tesseract (`spa`, `eng` o `spa+eng`).
        settings: ajustes del plugin en `config.json` (sin uso en esta spec).
        context: `PluginContext` que presta `preprocess()` para las variantes.

    Lanza `RuntimeError` si no se encuentra el ejecutable de Tesseract.
    """
    tesseract_path = resolve_tesseract_path()
    if tesseract_path is None:
        raise RuntimeError(
            "No se encontró el ejecutable de Tesseract. Indique su ruta desde Configuración."
        )

    config = load_config()
    min_word_confidence = config.get("min_word_confidence", 0)

    tiles = prepare_tiles_from_image(image)
    texts = [
        transcribe_image_variants(
            tile,
            language_code,
            tesseract_path,
            min_word_confidence,
            variants=context.preprocess(tile),
        )
        for tile in tiles
    ]
    return "\n".join(texts)
