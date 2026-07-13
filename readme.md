# OCR-Py

## Alcance del proyecto

Aplicativo de escritorio con Python para OCR (Optical Character Recognition), que transcribe imágenes a texto en español y en inglés, reconociendo la mayor cantidad de fuentes posible.

## Stack técnico

- **GUI:** PySide6.
- **OCR:** Tesseract, vía `pytesseract`. Requiere que el usuario instale Tesseract-OCR manualmente en el sistema ([instalador para Windows](https://github.com/UB-Mannheim/tesseract/wiki)).
- **Imágenes:** Pillow, para poder cargar y previsualizar cualquier formato de imagen.
- **Preprocesamiento:** numpy y opencv-python, para generar variantes de la imagen (mejora de OCR sobre fondos complejos y upscaling de imágenes chicas) y elegir la de mayor confianza.

Detalle completo del alcance, plan de implementación y decisiones en `specs/01-mvp-ocr-tesseract-tkinter.md`, `specs/02-ocr-imagenes-grandes.md`, `specs/03-preprocesamiento-ocr.md`, `specs/04-migracion-pyside6-menu-inicio.md` y `specs/05-menu-lateral-persistente.md`.

## Estado

La app transcribe imágenes con Tesseract, con soporte para imágenes grandes (tiling y downscale), preprocesamiento multi-variante para mejorar la precisión del OCR, GUI en PySide6 y menú lateral persistente. Ver `specs/` para el detalle de cada spec y su estado.

Limitación conocida: transcripciones sobre imágenes muy grandes pueden tardar; la app muestra un contador de segundos mientras procesa.

## Requisitos

- Python 3.10+
- Tesseract-OCR instalado en el sistema ([instalador para Windows](https://github.com/UB-Mannheim/tesseract/wiki)). Si no está en el PATH, la app pide la ruta al ejecutable la primera vez y la recuerda en `config.json`.

## Cómo correr la app

```bash
pip install -r requirements.txt
python main.py
```

## Estructura del código

```
main.py                        # punto de entrada
model/
  config_model.py              # lectura/escritura de config.json
  tesseract_locator.py         # detección del ejecutable de Tesseract
  ocr_model.py                 # transcripción vía pytesseract; orquesta tiling y preprocesamiento
  image_tiling.py              # tiling/downscale de imágenes grandes
  image_preprocessing.py       # variantes de preprocesamiento y selección por confianza
view/
  main_window.py                # ventana principal: sidebar + contenido, tema oscuro fijo
  sidebar_view.py                # menú lateral persistente
  ocr_view.py                    # widgets del flujo de OCR (abrir imagen, idioma, transcribir, preview, resultado)
controller/
  ocr_controller.py              # conecta eventos de la vista con el model, maneja errores y threading
```
