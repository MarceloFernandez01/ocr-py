# OCR-Py

## Alcance del proyecto

Buscamos crear un MVP de un aplicativo de OCR (Optical Character Recognition). El proyecto será un aplicativo de escritorio con Python, el cual debe transcribir imágenes a texto en español y en inglés, reconociendo la mayor cantidad de fuentes posible.

- Se debe evitar el uso de módulos externos salvo que sea estrictamente necesario.
- Se debe respetar el patrón MVC (Modelo, Vista y Controlador).

## Interfaz

La interfaz gráfica sí forma parte del MVP (ver `specs/01-mvp-ocr-tesseract-tkinter.md`). Por ahora será puramente funcional, sin diseño minimalista ni estilo "metro" — eso queda para una etapa posterior.

## Stack técnico (definido en la spec del MVP)

- **GUI:** Tkinter (librería estándar de Python).
- **OCR:** Tesseract, vía `pytesseract`. Requiere que el usuario instale Tesseract-OCR manualmente en el sistema ([instalador para Windows](https://github.com/UB-Mannheim/tesseract/wiki)).
- **Imágenes:** Pillow, para poder cargar y previsualizar cualquier formato de imagen.

Detalle completo del alcance, plan de implementación y decisiones en `specs/01-mvp-ocr-tesseract-tkinter.md`.

## Estado

El MVP está implementado y probado de punta a punta.

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
  tesseract_locator.py          # detección del ejecutable de Tesseract
  ocr_model.py                  # transcripción vía pytesseract
view/
  main_view.py                  # ventana y widgets Tkinter
controller/
  ocr_controller.py             # conecta eventos de la vista con el model
```
