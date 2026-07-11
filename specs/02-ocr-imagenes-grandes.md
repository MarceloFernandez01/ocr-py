# SPEC 02 — Reconocimiento de imágenes grandes / relación de aspecto extrema

> **Status:** Implementado
> **Depends on:** `specs/01-mvp-ocr-tesseract-tkinter.md`
> **Date:** 2026-07-09
> **Objective:** Hacer que la transcripción reconozca correctamente el texto de imágenes grandes o con relación de aspecto extrema (capturas, infografías), aplicando downscale y división en tiles antes de pasarlas a Tesseract, sin congelar la UI mientras procesa.

## Scope

**In:**

- **Downscale automático**: si el lado mayor de la imagen supera **3000px**, se redimensiona proporcionalmente antes de pasarla a Tesseract (usando Pillow, ya dependencia aprobada), preservando la imagen original para la vista previa.
- **Tiling automático**: si tras aplicar el umbral de 3000px por dimensión la imagen resultante todavía necesita partirse (relación de aspecto extrema), se divide en una **grilla dinámica de hasta 3x3** (filas/columnas calculadas según cuántas veces entra el umbral de 3000px en cada dimensión, con tope duro de 3x3), con **solapamiento entre tiles** para no cortar líneas de texto a la mitad.
- Cada tile se transcribe por separado con Tesseract (mismo idioma seleccionado por el usuario) y los resultados se **concatenan en orden, separados por salto de línea**, sin deduplicar el texto solapado.
- **Threading básico**: la transcripción (incluyendo el eventual downscale/tiling) corre en un hilo aparte para no congelar la ventana Tkinter. Mientras corre, el botón "Transcribir" se deshabilita.
- **Contador de segundos en vivo**: mientras procesa, el área de resultado muestra `Procesando... Ns` con `N` actualizándose cada ~200ms desde que arrancó la transcripción, hasta que termina (éxito o error).
- El threading, el tiling y el contador aplican también al flujo de reintento tras pedir la ruta de Tesseract manualmente (paso 8 de la spec 01).

**Out of scope (para futuras specs):**

- Deduplicación de texto repetido en zonas de solapamiento entre tiles.
- Indicador de progreso granular (ej. "tile 2 de 6") — solo se muestra el contador de segundos genérico.
- Cancelar una transcripción en curso.
- Preprocesamiento de imagen para mejorar precisión (binarización, enderezado, reducción de ruido) — sigue fuera de alcance como en la spec 01.
- Cambiar el umbral de 3000px o el tope 3x3 desde la UI o `config.json` — quedan como constantes en el código.

## Data model

Esta spec no introduce nuevas estructuras persistidas (no cambia `config.json`). Sí introduce constantes y una nueva forma de organizar la transcripción en memoria:

### Constantes (nuevo módulo `model/image_tiling.py`)

```python
MAX_DIMENSION = 3000   # px, lado máximo antes de downscale
MAX_GRID = 3           # tope de filas/columnas en la grilla de tiling
TILE_OVERLAP_RATIO = 0.10  # 10% de solapamiento entre tiles
```

### Funciones nuevas

```python
def prepare_tiles(image_path: str) -> list[Image.Image]:
    """Aplica downscale si corresponde y devuelve la lista de tiles (imágenes en memoria)
    a transcribir por separado. Si la imagen no supera el umbral, devuelve una lista
    de un solo elemento (la imagen sin modificar)."""
```

- Vive en `model/image_tiling.py` (no importa Tkinter, respeta MVC).
- `model/ocr_model.py` se extiende con una función que orquesta `prepare_tiles(...)` + `transcribe(...)` por tile + concatenación del resultado.

### Estado en memoria del Controller

Se agrega un flag de estado a `AppState` (o se maneja localmente en el Controller) para saber si hay una transcripción en curso y así evitar disparar otra en paralelo mientras el botón está deshabilitado.

## Implementation plan

1. **Model — `image_tiling.py`.** Crear `model/image_tiling.py` con las constantes (`MAX_DIMENSION`, `MAX_GRID`, `TILE_OVERLAP_RATIO`) y `prepare_tiles(image_path)`: calcula downscale proporcional si el lado mayor supera `MAX_DIMENSION`, luego calcula la grilla dinámica (filas/columnas según cuántas veces entra `MAX_DIMENSION` en cada dimensión, tope `MAX_GRID`x`MAX_GRID`) y recorta los tiles con solapamiento. Si no hace falta partir, devuelve `[imagen_completa]`.
   Prueba manual: invocar `prepare_tiles(...)` desde consola con una imagen pequeña (debe devolver 1 tile) y con una imagen grande/ancha (debe devolver varios tiles con overlap visible al guardarlos).

2. **Model — orquestación en `ocr_model.py`.** Agregar una función (ej. `transcribe_large_image(image_path, language_code, tesseract_path)`) que llama a `prepare_tiles(...)`, transcribe cada tile con la `transcribe(...)` existente y concatena los resultados con salto de línea. Mantener `transcribe(...)` intacta para no romper su uso directo.
   Prueba manual: invocar la nueva función desde consola con una imagen grande de prueba y verificar que el texto concatenado tiene sentido (con cierta redundancia esperada en los bordes).

3. **Controller — threading con contador de segundos.** Modificar `controller/ocr_controller.py` para que la acción del botón "Transcribir" dispare la transcripción en un `threading.Thread`. Antes de lanzar el hilo: deshabilitar el botón, guardar el instante de inicio (`time.monotonic()`) y arrancar un loop en el hilo principal (`view.after(200, ...)`) que actualiza el resultado con `Procesando... Ns` mientras el hilo siga vivo. Al terminar el hilo (éxito o error), detener el loop del contador y actualizar la UI con el resultado final, reactivando el botón.
   Prueba manual: cargar una imagen grande, presionar "Transcribir", confirmar que el contador sube visiblemente (~cada 200ms) mientras la ventana sigue respondiendo, y que al terminar se ve el resultado y el botón vuelve a estar habilitado.

4. **Controller — usar la nueva función de transcripción.** Cambiar el Controller para que llame a `transcribe_large_image(...)` (en vez de `transcribe(...)` directo) tanto en el flujo normal como en el de reintento tras pedir la ruta de Tesseract manualmente.
   Prueba manual: repetir el flujo de "Tesseract no encontrado" de la spec 01 con una imagen grande y confirmar que también tiliza, cuenta segundos y usa threading correctamente.

5. **Controller — evitar transcripciones concurrentes.** Agregar el flag de "transcripción en curso" para que, si por algún motivo se dispara "Transcribir" mientras ya hay un hilo corriendo, no se lance un segundo hilo ni un segundo loop de contador.
   Prueba manual: revisar que no haya forma trivial de hacer doble click y disparar dos hilos (ej. deshabilitando el botón inmediatamente al primer click, antes de lanzar el hilo).

## Acceptance criteria

- [X] Si una imagen tiene el lado mayor por debajo de 3000px, la transcripción funciona igual que antes (sin downscale ni tiling), con resultado idéntico al comportamiento actual.
- [X] Si una imagen supera 3000px en su lado mayor, se le aplica downscale proporcional antes de pasarla a Tesseract, sin alterar la imagen mostrada en la vista previa.
- [X] Si tras el downscale la imagen sigue necesitando partirse por su relación de aspecto, se divide en una grilla dinámica de hasta 3x3 tiles con solapamiento entre ellos.
- [X] El texto transcrito de cada tile se concatena en orden con salto de línea, sin intentar deduplicar el contenido solapado.
- [X] Al presionar "Transcribir", el botón se deshabilita inmediatamente y no puede dispararse una segunda transcripción en paralelo mientras la primera está en curso.
- [X] Mientras la transcripción está en curso, el área de resultado muestra `Procesando... Ns`, con `N` incrementándose visiblemente cada ~200ms.
- [X] La ventana de Tkinter sigue respondiendo (se puede mover/redimensionar) mientras la transcripción está en curso, incluso con imágenes grandes.
- [X] Al terminar la transcripción (éxito o error), el contador se detiene, se muestra el resultado final (o el mensaje de error) y el botón "Transcribir" se reactiva.
- [X] El flujo de "Tesseract no encontrado" (pedir ruta manual) sigue funcionando igual que en la spec 01, ahora también con threading, contador y tiling aplicados al reintento.
- [X] El código nuevo respeta MVC: `model/image_tiling.py` no importa Tkinter; el threading y la actualización de UI viven en el Controller.

## Decisions

- **Sí:** Downscale proporcional con umbral fijo de **3000px** de lado mayor. Balance razonable entre preservar legibilidad del texto y evitar los problemas conocidos de Tesseract con imágenes muy grandes.
- **Sí:** Tiling con grilla dinámica (tope 3x3) en vez de una grilla fija siempre activa. Evita llamadas innecesarias a Tesseract en imágenes que solo superan el umbral levemente.
- **Sí:** Solapamiento del 10% entre tiles. Reduce el riesgo de cortar líneas de texto justo en el borde de un tile.
- **No:** Deduplicar texto repetido por el solapamiento. Agrega complejidad (diff de líneas) que no se justifica para este MVP; se acepta cierta redundancia en el resultado como limitación conocida.
- **Sí:** Concatenación simple del texto de cada tile en orden, separado por salto de línea. Consistente con la filosofía de mantener el MVP simple.
- **Sí:** Threading básico (`threading.Thread` + `view.after(...)`) en vez de dejar la UI congelada. El tiling multiplica la cantidad de llamadas a Tesseract, así que el tiempo de espera puede crecer notablemente y congelar la ventana sería peor experiencia que hoy.
- **No:** Indicador de progreso granular por tile (ej. "tile 2 de 6"). Un contador de segundos genérico es suficiente feedback para el usuario sin la complejidad de reportar progreso por tile desde el hilo secundario.
- **Sí:** Contador de segundos actualizado cada ~200ms en el área de resultado existente. Reutiliza el widget ya existente en vez de agregar un widget nuevo a la View.
- **No:** Cancelar una transcripción en curso. Fuera de alcance de este MVP; si se vuelve necesario (ej. imágenes que tardan minutos), se evalúa en spec futura.
- **No:** Configurar el umbral de 3000px o el tope 3x3 desde `config.json` o la UI. Quedan como constantes en el código para no agregar complejidad de configuración a un ajuste interno de rendimiento.

## Risks

| Risk | Mitigation |
|---|---|
| El downscale a 3000px reduce demasiado la legibilidad en imágenes con texto muy pequeño, empeorando el reconocimiento en vez de mejorarlo. | Se acepta como trade-off conocido de este MVP; si se vuelve un problema recurrente, evaluar un umbral configurable o un algoritmo de resize más cuidadoso en spec futura. |
| El tiling con solapamiento del 10% no es suficiente y sigue cortando palabras justo en el borde de dos tiles. | Se acepta como limitación conocida (parte del trade-off de no deduplicar); el resultado sigue siendo mejor que el texto vacío/incompleto actual. |
| Imágenes extremadamente grandes generan una grilla 3x3 (9 tiles), multiplicando por 9 el tiempo de transcripción. | El contador de segundos en vivo comunica al usuario que la app sigue trabajando en vez de parecer colgada; el tope 3x3 evita que la cantidad de tiles crezca sin límite. |
| Errores en un tile individual (ej. Tesseract falla en un tile específico) podrían interrumpir toda la transcripción. | El manejo de excepciones existente (spec 01, paso 9) debe envolver el loop de tiles; si no se resuelve en el detalle de implementación, queda como riesgo a validar durante `/spec-impl`. |
| El hilo secundario podría intentar actualizar la UI directamente en vez de vía `view.after(...)`, causando errores de Tkinter (no es thread-safe). | El plan de implementación (paso 3) especifica explícitamente usar `view.after(...)` para toda actualización de UI desde el resultado del hilo. |
