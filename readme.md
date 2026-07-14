# OCR-Py

## Alcance del proyecto

Aplicativo de escritorio con Python para OCR (Optical Character Recognition), que transcribe imágenes a texto en español y en inglés, reconociendo la mayor cantidad de fuentes posible. Incluye OCR en vivo sobre un segmento de pantalla y traducción offline del texto reconocido.

## Stack técnico

- **GUI:** PySide6.
- **OCR:** Tesseract, vía `pytesseract`. Requiere que el usuario instale Tesseract-OCR manualmente en el sistema ([instalador para Windows](https://github.com/UB-Mannheim/tesseract/wiki)).
- **Imágenes:** Pillow, para poder cargar y previsualizar cualquier formato de imagen.
- **Preprocesamiento:** numpy y opencv-python, para generar variantes de la imagen (mejora de OCR sobre fondos complejos y upscaling de imágenes chicas) y elegir la de mayor confianza.
- **Traducción:** argostranslate, para traducir offline el texto reconocido en OCR en vivo.

## Estado

La app transcribe imágenes con Tesseract, con soporte para imágenes grandes (tiling y downscale), preprocesamiento multi-variante para mejorar la precisión del OCR y recorte de región opcional antes de transcribir. Incluye OCR en vivo (captura periódica de un segmento de pantalla con overlay flotante, detección de cambios y traducción offline opcional). GUI en PySide6 con skin visual estilo Metro, menú lateral persistente y una vista de Configuración con toggle de tema claro/oscuro en caliente (persistido en `config.json`).

Limitación conocida: transcripciones sobre imágenes muy grandes pueden tardar; la app muestra un contador de segundos mientras procesa.

## Requisitos

- Python 3.10+
- Tesseract-OCR instalado en el sistema ([instalador para Windows](https://github.com/UB-Mannheim/tesseract/wiki)). Si no está en el PATH, la app pide la ruta al ejecutable la primera vez y la recuerda en `config.json`.

## Cómo correr la app

```bash
pip install -r requirements.txt
python main.py
```

## Cómo correr las pruebas unitarias

Pruebas de integración real (sin mocks) sobre OCR y traducción: transcriben imágenes con texto conocido usando el Tesseract instalado en el sistema y traducen frases conocidas con `argostranslate`.

```bash
pip install -r requirements-dev.txt
python -m pytest tests -v
```

- Si Tesseract no está instalado o no se puede localizar, los tests de OCR se saltan (`skip`) en vez de fallar.
- Los tests de traducción es↔en descargan el modelo de `argostranslate` la primera vez (requiere internet); si la descarga falla, también se saltan con un mensaje.

## Estructura del código

```
main.py                        # punto de entrada
model/
  config_model.py              # lectura/escritura de config.json (incluye tema)
  tesseract_locator.py         # detección del ejecutable de Tesseract
  ocr_model.py                 # transcripción vía pytesseract; orquesta tiling y preprocesamiento
  image_tiling.py              # tiling/downscale de imágenes grandes
  image_preprocessing.py       # variantes de preprocesamiento y selección por confianza
  image_diff.py                # comparación de capturas de pantalla para detectar cambios (OCR en vivo)
  translation_model.py         # traducción offline del texto reconocido vía argostranslate
view/
  main_window.py                # ventana principal: sidebar + contenido, aplica tema en caliente
  sidebar_view.py                # menú lateral persistente (OCR de imágenes, OCR en vivo, engranaje de Configuración)
  ocr_view.py                    # widgets del flujo de OCR (abrir imagen, idioma, recorte, transcribir, preview, resultado)
  live_ocr_view.py                # pantalla de OCR en vivo: overlay de captura y control de transcripción por polling
  screen_overlay.py               # overlay flotante para seleccionar el segmento de pantalla a capturar
  settings_view.py               # vista de Configuración: switch de tema claro/oscuro y placeholder de motor OCR
  metro_style.py                 # QSS estilo Metro (variantes oscura/clara), única fuente del skin visual
  assets/                        # íconos (chevron de QComboBox por tema)
controller/
  ocr_controller.py              # conecta eventos de la vista con el model, maneja errores y threading
  live_ocr_controller.py         # ciclo de OCR en vivo: captura, diff, transcripción por polling
  settings_controller.py         # conecta el toggle de tema con el model y con MainWindow
tests/
  conftest.py                    # helpers: skip si no hay Tesseract, generación de imágenes con texto
  test_ocr_model.py               # pruebas de integración real de transcripción (Tesseract)
  test_translation_model.py       # pruebas de integración real de traducción (argostranslate)
```
