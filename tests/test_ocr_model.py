"""Pruebas de integración real del reconocimiento de texto con Tesseract."""

from model.ocr_model import transcribe, transcribe_image_variants

from conftest import make_text_image, normalizar, require_tesseract


def test_transcribe_texto_ingles(tmp_path):
    tesseract_path = require_tesseract()
    image = make_text_image("Hello world")
    image_path = tmp_path / "hello.png"
    image.save(image_path)

    resultado = transcribe(str(image_path), "eng", tesseract_path)

    assert "hello world" in normalizar(resultado)


def test_transcribe_texto_espanol(tmp_path):
    tesseract_path = require_tesseract()
    image = make_text_image("El nino comio")
    image_path = tmp_path / "espanol.png"
    image.save(image_path)

    resultado = transcribe(str(image_path), "spa", tesseract_path)

    normalizado = normalizar(resultado)
    assert "nino" in normalizado
    assert "comio" in normalizado


def test_transcribe_image_variants_en_memoria():
    tesseract_path = require_tesseract()
    image = make_text_image("Testing OCR")

    resultado = transcribe_image_variants(image, "eng", tesseract_path)

    assert "testing ocr" in normalizar(resultado)
