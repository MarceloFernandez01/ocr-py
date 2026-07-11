# SPEC 03 — Preprocesamiento de imagen para OCR de texto sobre fondos complejos

> **Status:** Aprobado
> **Depends on:** `specs/02-ocr-imagenes-grandes.md`
> **Date:** 2026-07-10
> **Objective:** Lograr que la app transcriba texto estilizado sobre fondos de color o
> con gradiente (donde hoy Tesseract devuelve vacío) generando varias variantes
> preprocesadas de cada tile y eligiendo automáticamente la de mayor confianza.

## Scope

**In:**

- **Nuevo módulo `model/image_preprocessing.py`** que, dada una imagen PIL, devuelve un
  conjunto fijo de variantes preprocesadas (incluida siempre la original sin tocar).
- **Aprobación de dependencias:** `numpy` y `opencv-python` pasan a ser dependencias
  aprobadas del proyecto (junto a `pytesseract` y `Pillow`). Se agregan a `requirements.txt`.
- **Conjunto fijo de variantes** (constante en el código, ampliable en specs futuras):
  1. `original` — la imagen sin modificar (garantiza no-regresión).
  2. `gris_autocontraste` — escala de grises + normalización/autocontraste.
  3. `otsu` — grises + umbral global de Otsu (texto oscuro sobre fondo claro).
  4. `otsu_invertido` — Otsu invertido (texto claro sobre fondo oscuro).
  5. `adaptativo` — umbral adaptativo gaussiano (`cv2.adaptiveThreshold`), para gradientes.
  6. `canal_color` — canal de mayor contraste/varianza + Otsu (texto separado por color,
     ej. naranja sobre violeta).
- **Selección por confianza, por tile:** para cada tile (los que ya produce
  `prepare_tiles` de la spec 02), se transcribe cada variante con
  `pytesseract.image_to_data`, se calcula la **confianza media de las palabras** con
  `conf >= 0` y texto no vacío, y se elige la variante de mayor confianza. Empate o todas
  vacías → gana `original`. El texto final del tile se toma de la variante ganadora.
- Los textos ganadores de cada tile se concatenan en orden con salto de línea (igual que
  hoy).
- Integración transparente: se hace dentro de `transcribe_large_image`, así que hereda el
  threading + contador de segundos + flujo de "Tesseract no encontrado" de la spec 02 sin
  tocar el Controller ni la View.

**Out of scope (para futuras specs):**

- Configurar/activar el preprocesamiento desde la GUI (checkbox, sliders) — es automático.
- Mostrar en la GUI qué variante ganó o una vista previa de la imagen preprocesada.
- Enderezado (deskew), reducción de ruido morfológica avanzada, detección de regiones de
  texto (MSER) más allá de las 6 variantes definidas.
- Deduplicación del texto solapado entre tiles (sigue fuera de alcance, viene de spec 02).
- Optimizar la cantidad de llamadas a Tesseract (multi-variante × tiles) — se acepta el
  costo; el contador de segundos comunica la espera.
- Cambiar el conjunto de variantes o la métrica de confianza desde `config.json`.

## Data model

No introduce estructuras persistidas (no cambia `config.json`). Introduce un módulo nuevo:

### `model/image_preprocessing.py`

```python
def generate_variants(image: Image.Image) -> list[tuple[str, Image.Image]]:
    """Devuelve el conjunto fijo de variantes preprocesadas de `image`.

    El primer elemento siempre es ("original", image) para garantizar no-regresión.
    El resto aplica escala de grises, autocontraste, Otsu (directo e invertido),
    umbral adaptativo y separación por canal de color, usando cv2/numpy.
    No importa Tkinter ni pytesseract (respeta MVC).
    """
```

### `model/ocr_model.py` (helper de selección)

```python
def _transcribe_best_variant(tile, language_code) -> str:
    """Transcribe todas las variantes del tile, puntúa cada una por confianza media
    de palabra (conf >= 0) y devuelve el texto de la de mayor confianza; empate o
    vacías → 'original'."""
```

`transcribe_large_image` pasa de `image_to_string` por tile a `_transcribe_best_variant`
por tile.

## Implementation plan

1. **Dependencias.** Agregar `numpy` y `opencv-python` a `requirements.txt`. Actualizar la
   nota de dependencias aprobadas en `CLAUDE.md` para reflejar que ahora son cuatro.
   Prueba: `python -c "import cv2, numpy"` sin error.
2. **Model — `image_preprocessing.py`.** Crear el módulo con `generate_variants(image)` y
   las 6 variantes. Conversión PIL↔numpy (cuidando orden RGB/BGR). Cada variante devuelve
   una `Image.Image`.
   Prueba manual: correr sobre las dos capturas y guardar cada variante a disco para
   inspeccionar visualmente que al menos una deja el texto legible/binarizado.
3. **Model — selección en `ocr_model.py`.** Agregar `_transcribe_best_variant(tile, lang)`
   usando `image_to_data(..., output_type=Output.DICT)` para puntuar por confianza media,
   con desempate a `original`. Cambiar `transcribe_large_image` para usarlo por tile.
   Mantener `transcribe(...)` intacta.
   Prueba manual: transcribir las dos capturas desde la app y confirmar que ahora sale
   texto sustancialmente correcto; transcribir una imagen limpia previa y confirmar que no
   empeora (gana `original` o una variante equivalente).
4. **Verificación de integración.** Confirmar en la app que threading, contador de segundos
   y flujo de "Tesseract no encontrado" siguen funcionando (más lento por las variantes).

## Acceptance criteria

- [ ] `numpy` y `opencv-python` están en `requirements.txt` y `python -c "import cv2, numpy"`
      corre sin error.
- [ ] `model/image_preprocessing.py` existe, no importa Tkinter ni pytesseract, y
      `generate_variants(img)` devuelve una lista cuyo primer elemento es `("original", img)`.
- [ ] Para cada tile se transcriben todas las variantes, se puntúa por confianza media de
      palabra (`conf >= 0`, texto no vacío) y se elige la de mayor confianza; empate/vacías
      → `original`.
- [ ] Las **dos capturas del usuario** (texto con contorno sobre cielo/gradiente) ahora
      producen una transcripción sustancialmente correcta: la mayoría de las líneas/palabras
      legibles se reconocen, en vez del resultado vacío/basura actual.
- [ ] Una imagen limpia que ya se transcribía bien antes no empeora (gana `original` u otra
      variante de calidad equivalente): sin regresión.
- [ ] El resultado de cada tile se concatena en orden con salto de línea, igual que antes.
- [ ] El Controller, la vista previa y `config.json` no cambian; threading, contador de
      segundos y flujo de "Tesseract no encontrado" siguen funcionando.
- [ ] MVC respetado: `image_preprocessing.py` sin Tkinter ni pytesseract; los llamados a
      Tesseract y la selección viven en `ocr_model.py`.

## Decisions

- **Sí:** aprobar `numpy` + `opencv-python` como dependencias. El umbral adaptativo y la
  separación por canal son necesarios para el texto sobre gradientes; Pillow solo no alcanza.
- **Sí:** multi-variante con selección automática por confianza, sin control en la GUI.
  Evita que el usuario tenga que adivinar qué preprocesamiento aplicar.
- **Sí:** incluir siempre la `original` como candidata. Garantiza que nunca se empeora una
  imagen que hoy funciona.
- **Sí:** selección **por tile** (no global). Más robusta cuando el fondo varía; las
  imágenes objetivo son de un solo tile, así que no se penalizan.
- **Sí:** conjunto fijo de 6 variantes como constante en el código, no configurable.
  Mantiene el MVP simple; ampliar el set queda para spec futura.
- **Sí:** confianza = media de `conf` de palabras (`conf >= 0`) vía `image_to_data`. Métrica
  simple y disponible en pytesseract sin dependencias extra.
- **No:** mostrar la variante ganadora o la imagen preprocesada en la GUI. Feedback
  innecesario para el MVP de esta feature.
- **No:** optimizar la cantidad de llamadas a Tesseract. Se acepta el costo; el contador de
  segundos de la spec 02 ya comunica la espera.

## Risks

| Risk | Mitigation |
|---|---|
| Multi-variante × tiling multiplica las llamadas a Tesseract (hasta 6 variantes × 9 tiles), volviendo lenta la transcripción de imágenes grandes. | El contador de segundos en vivo (spec 02) comunica que sigue trabajando; el tope 3x3 acota los tiles. Optimizar queda como spec futura. |
| El texto con contorno decorativo puede seguir dejando errores sueltos aun con la mejor variante. | Objetivo declarado como "sustancialmente correcto", no carácter-perfecto; se acepta como límite conocido. |
| La confianza media de Tesseract puede ser alta en una variante con texto incorrecto ("confidently wrong"), eligiendo una peor variante. | Incluir siempre la `original` acota el peor caso; si se vuelve recurrente, evaluar una métrica de selección mejor en spec futura. |
| Bug de orden de canales RGB/BGR al convertir PIL↔OpenCV, degradando la separación por color. | El paso 2 del plan explicita cuidar la conversión y validar visualmente cada variante guardándola a disco. |
| `opencv-python` es una dependencia pesada; puede complicar la instalación en la máquina del usuario. | Decisión consciente ya tomada; se documenta en `requirements.txt`. Si molesta, evaluar `opencv-python-headless` en el futuro. |
