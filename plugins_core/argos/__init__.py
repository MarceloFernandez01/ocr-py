"""Plugin esencial: traducción offline vía `argostranslate`.

Envoltorio fino sobre `model/translation_model.py`; la lógica de esa spec
no se mueve ni se reescribe. `model/translation_model.py` ya difiere el
import de `argostranslate` a la función que lo necesita, así que importar
`translate_text` acá no paga ese costo al cargar el plugin.
"""

from model.translation_model import translate_text


def translate(text: str, source_lang: str, target_lang: str, settings: dict, context) -> str:
    """Traduce `text` de `source_lang` a `target_lang` (códigos internos `"spa"`/`"eng"`)."""
    return translate_text(text, source_lang, target_lang)
