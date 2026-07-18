"""Traducción offline del texto reconocido mediante `argostranslate`.

Los imports de `argostranslate` son diferidos (dentro de cada función) porque
`argostranslate.translate` tarda ~2.5s en importarse, y este módulo se
importa transitivamente al construir `MainWindow`: un import a nivel de
módulo agregaría ese costo a cada arranque de la app aunque nunca se use
la traducción.
"""

LANGUAGE_CODE_MAP = {
    "spa": "es",
    "eng": "en",
}
"""Mapea los códigos internos de idioma (los mismos que usa `model/ocr_model.py`
para Tesseract) a los códigos ISO de dos letras que espera `argostranslate`."""


def _ensure_package_installed(source_code: str, target_code: str) -> None:
    """Instala el paquete de idioma origen/destino de `argostranslate` si falta.

    Busca en los paquetes ya instalados; si no está, lo busca entre los
    disponibles remotamente, lo descarga e instala.
    """
    import argostranslate.package
    import argostranslate.translate

    installed_languages = argostranslate.translate.get_installed_languages()
    installed_codes = {lang.code for lang in installed_languages}
    if source_code in installed_codes and target_code in installed_codes:
        source_lang = next(lang for lang in installed_languages if lang.code == source_code)
        if source_lang.get_translation(
            next(lang for lang in installed_languages if lang.code == target_code)
        ):
            return

    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    package = next(
        pkg
        for pkg in available_packages
        if pkg.from_code == source_code and pkg.to_code == target_code
    )
    downloaded_path = package.download()
    argostranslate.package.install_from_path(downloaded_path)


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Traduce `text` de `source_lang` a `target_lang` (códigos internos "spa"/"eng").

    Si `source_lang == target_lang`, devuelve `text` sin modificar. Si el
    paquete de idioma para el par origen/destino no está instalado, lo busca
    en `argostranslate.package.get_available_packages()`, lo descarga
    (`argostranslate.package.install_from_path`) y recién entonces traduce.
    """
    if source_lang == target_lang:
        return text

    import argostranslate.translate

    source_code = LANGUAGE_CODE_MAP[source_lang]
    target_code = LANGUAGE_CODE_MAP[target_lang]

    _ensure_package_installed(source_code, target_code)

    return argostranslate.translate.translate(text, source_code, target_code)
