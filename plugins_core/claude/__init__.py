"""Plugin esencial: motor de OCR vía Claude Haiku 4.5 (API de Anthropic).

Envoltorio fino sobre `model/claude_ocr_model.py` y `model/claude_usage_model.py`;
la lógica de esas specs no se mueve ni se reescribe. Ignora `context.preprocess`:
Claude no tiene una métrica de confianza propia para elegir entre variantes.
"""

from PIL import Image

from model.claude_ocr_model import transcribe_image_claude
from model.claude_usage_model import register_call


def _translate_error(error: Exception) -> Exception:
    """Traduce una excepción del SDK `anthropic` a una con mensaje legible en español.

    Import perezoso de `anthropic`: esta función solo se llama tras una
    transcripción fallida con este plugin. El registro de plugins envuelve
    el resultado en `PluginError`, así que alcanza con devolver una
    excepción con el mensaje traducido en vez de una excepción propia del SDK.
    """
    import anthropic

    if isinstance(error, anthropic.AuthenticationError):
        return RuntimeError("La API key de Anthropic no es válida. Por favor cambiarla desde Configuración.")
    if isinstance(error, anthropic.APIConnectionError):
        return RuntimeError("No se pudo conectar con la API de Anthropic. Por favor revise la conexión a internet.")
    if isinstance(error, anthropic.RateLimitError):
        return RuntimeError(
            "Se alcanzó el límite de uso (rate limit) de la API de Anthropic. "
            "Espere unos minutos y vuelva a intentar."
        )
    if isinstance(error, anthropic.APIStatusError):
        detail = error.message
        if isinstance(error.body, dict):
            detail = error.body.get("error", {}).get("message", detail)
        return RuntimeError(f"La API de Anthropic devolvió un error ({error.status_code}): {detail}")
    return error


def transcribe(image: Image.Image, language_code: str, settings: dict, context) -> str:
    """Transcribe `image` con Claude Haiku 4.5 y registra el gasto de la llamada.

    Args:
        image: imagen ya cargada en memoria a transcribir.
        language_code: código de idioma (`spa`, `eng` o `spa+eng`).
        settings: ajustes del plugin ya resueltos por el registro;
            `settings["api_key"]` viene del keyring del sistema operativo.
        context: `PluginContext` del registro; no se usa (ver docstring del módulo).

    Las excepciones del SDK `anthropic` se traducen a un mensaje legible en
    español antes de propagarse; el registro de plugins las envuelve en
    `PluginError` nombrando este plugin.
    """
    api_key = settings.get("api_key")

    try:
        text, input_tokens, output_tokens = transcribe_image_claude(image, language_code, api_key)
    except Exception as error:
        raise _translate_error(error) from error

    register_call(input_tokens, output_tokens)
    return text
