"""Plugin esencial: motor de OCR vía Claude Haiku 4.5 (API de Anthropic).

Envoltorio fino sobre `model/claude_ocr_model.py` y `model/claude_usage_model.py`;
la lógica de esas specs no se mueve ni se reescribe. Ignora `context.preprocess`:
Claude no tiene una métrica de confianza propia para elegir entre variantes.
"""

import keyring
from PIL import Image

from model.claude_ocr_model import transcribe_image_claude
from model.claude_usage_model import register_call
from model.config_model import KEYRING_SERVICE, KEYRING_USERNAME


def transcribe(image: Image.Image, language_code: str, settings: dict, context) -> str:
    """Transcribe `image` con Claude Haiku 4.5 y registra el gasto de la llamada.

    Args:
        image: imagen ya cargada en memoria a transcribir.
        language_code: código de idioma (`spa`, `eng` o `spa+eng`).
        settings: ajustes del plugin; `settings["api_key"]` tiene prioridad
            sobre la API key guardada en el keyring del sistema operativo.
        context: `PluginContext` del registro; no se usa (ver docstring del módulo).

    Lanza las excepciones propias del SDK `anthropic` sin capturarlas; quien
    llama a esta función (`model/plugin_registry.run_ocr`) las envuelve en
    `PluginError`.
    """
    api_key = settings.get("api_key") or keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)

    text, input_tokens, output_tokens = transcribe_image_claude(image, language_code, api_key)
    register_call(input_tokens, output_tokens)
    return text
