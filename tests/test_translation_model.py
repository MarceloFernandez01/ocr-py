"""Pruebas de integración real de la traducción offline con argostranslate."""

import pytest

from model.translation_model import translate_text

from conftest import normalizar


def test_passthrough_mismo_idioma():
    assert translate_text("Hola", "spa", "spa") == "Hola"


def test_traduce_espanol_a_ingles():
    try:
        resultado = translate_text("El gato es negro", "spa", "eng")
    except Exception as exc:
        pytest.skip(f"No se pudo descargar/instalar el modelo de traducción: {exc}")

    normalizado = normalizar(resultado)
    assert "cat" in normalizado
    assert "black" in normalizado


def test_traduce_ingles_a_espanol():
    try:
        resultado = translate_text("Hello world", "eng", "spa")
    except Exception as exc:
        pytest.skip(f"No se pudo descargar/instalar el modelo de traducción: {exc}")

    normalizado = normalizar(resultado)
    assert "hola" in normalizado or "mundo" in normalizado
