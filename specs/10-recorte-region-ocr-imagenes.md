# SPEC 10 — Recorte de región antes de transcribir en OCR de imágenes

> **Status:** Implementado
> **Depends on:** `specs/01-mvp-ocr-tesseract-tkinter.md`, `specs/02-ocr-imagenes-grandes.md`, `specs/03-preprocesamiento-ocr.md`, `specs/09-live-ocr-boton-iniciar-transcripcion.md`
> **Date:** 2026-07-13
> **Objective:** Permitir seleccionar arrastrando un rectángulo sobre la vista previa de `OcrView` para que "Transcribir" procese solo esa región de la imagen en vez de la imagen completa.

## Scope

**In:**

- **`view/ocr_view.py`**: un único botón `crop_button`, checkable, cuyo texto alterna entre "Activar recorte" (sin región seleccionada) y "Quitar recorte" (con región seleccionada). Envuelto en `QVBoxLayout` con `QLabel("")` espaciador, siguiendo la convención de alineación de spec 09, ubicado en `left_toolbar` junto a `open_button`. Señal única `crop_toggled` (al clickear el botón, sea cual sea su estado). Un `QRubberBand` se instala sobre `preview_label` para dibujar la selección durante el arrastre y queda visible (congelado) tras soltar el mouse, mostrando el área que se transcribirá. Método `update_crop_button(has_crop: bool, armed: bool)` (setea texto y estado `checked` según haya región o esté armado el modo), `show_crop_rect(rect: QRect)`, `hide_crop_rect()`.
- **`controller/ocr_controller.py`**: nuevo estado `self._crop_box: tuple[int, int, int, int] | None` (coordenadas en la imagen original, no en la preview). Maneja el ciclo: click en el botón (`on_crop_toggled`) → si ya hay `_crop_box`, lo limpia (equivalente a "Quitar recorte"); si no, alterna `self._crop_mode_active` (equivalente a "Activar recorte", con un segundo click para cancelar el armado). El arrastre sobre `preview_label` se habilita vía `eventFilter` cuando `self._crop_mode_active` **o** ya existe `self._crop_box` — esto permite redefinir la región arrastrando de nuevo sin pasar por el botón. Al soltar, si el rectángulo supera el umbral mínimo, mapea las coordenadas de la preview (que puede tener letterboxing por `ImageOps.contain`) a coordenadas de la imagen original, guarda `self._crop_box` y actualiza el botón a "Quitar recorte"; si no supera el umbral, conserva el recorte previo (si existía) o cancela el armado (si no). `on_open_image()` resetea `self._crop_box`/`self._crop_mode_active` y el botón al cargar una imagen nueva. `on_transcribe()` recorta `self._preview_source` (imagen en resolución original) con `self._crop_box` si está seteado antes de lanzar `TranscriptionWorker`.
- **`model/image_tiling.py`**: se extrae `prepare_tiles_from_image(image: Image.Image) -> list[Image.Image]` con la lógica actual de `prepare_tiles`, y `prepare_tiles(image_path)` pasa a abrir la imagen y delegar en la nueva función. Sin cambio de comportamiento para los llamadores existentes.
- **`model/ocr_model.py`**: nueva función pública `transcribe_cropped_image(image: Image.Image, language_code: str, tesseract_path: str | None) -> str`, análoga a `transcribe_large_image` pero recibiendo una `PIL.Image` ya recortada en memoria en vez de una ruta: aplica `prepare_tiles_from_image` + `transcribe_image_variants` por tile igual que `transcribe_large_image`.
- **`controller/ocr_controller.py`**: `TranscriptionWorker` gana un parámetro opcional `image: Image.Image | None` — si viene seteado, el worker llama a `transcribe_cropped_image(image, ...)` en vez de `transcribe_large_image(image_path, ...)`.
- **`view/metro_style.py`**: estilo para `crop_button` (mismo patrón que otros `QPushButton`, con selector `:checked` compartido tanto para "armado" como para "con recorte") y para el `QRubberBand` (color de acento, coherente con el borde de `ScreenOverlay` de spec 08), en ambos temas.

**Out:**

- No se toca `LiveOcrView` ni `ScreenOverlay`; el recorte de región en OCR en vivo ya está cubierto por el overlay (spec 08) y queda fuera de alcance.
- No se persiste el recorte entre imágenes, navegaciones de sidebar, ni sesiones.
- No se permite mover/redimensionar el rectángulo ya dibujado con handles (solo redefinirlo por completo arrastrando de nuevo, o quitarlo con el botón).
- No se agrega zoom ni herramientas de edición de imagen adicionales (solo el rectángulo de recorte).
- La vista previa (`preview_label`) sigue mostrando siempre la imagen completa; no se reemplaza por el recorte (ya definido: el recorte solo afecta la transcripción).

## Data model

```python
# model/image_tiling.py (refactor, sin cambio de comportamiento externo)

def prepare_tiles_from_image(image: Image.Image) -> list[Image.Image]:
    """Misma lógica que ya tenía `prepare_tiles` (downscale y/o tiling según
    `MAX_DIMENSION`/`MAX_GRID`), aplicada sobre una `PIL.Image` ya en memoria
    en vez de una ruta. `prepare_tiles(image_path)` pasa a ser un wrapper que
    abre la imagen y delega acá."""


def prepare_tiles(image_path: str) -> list[Image.Image]:
    """Abre `image_path` y delega en `prepare_tiles_from_image`. Firma y
    comportamiento externo sin cambios."""
```

```python
# model/ocr_model.py (ampliación)

def transcribe_cropped_image(image: Image.Image, language_code: str, tesseract_path: str | None) -> str:
    """Transcribe una `PIL.Image` ya recortada en memoria, aplicando
    `prepare_tiles_from_image` + `transcribe_image_variants` por tile — misma
    lógica que `transcribe_large_image`, pero partiendo de una imagen ya
    recortada en memoria en vez de leer y recortar desde `image_path`."""
```

```python
# controller/ocr_controller.py (ampliación)

class TranscriptionWorker(QThread):
    def __init__(
        self,
        image_path: str,
        language_code: str,
        tesseract_path: str | None,
        cropped_image: Image.Image | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Si `cropped_image` no es None, `run()` llama a `transcribe_cropped_image`
        en vez de `transcribe_large_image`, ignorando `image_path` para la
        transcripción (se mantiene solo por compatibilidad de firma/logs)."""


class OcrController(QObject):
    # Nuevo estado en memoria (no en AppState, que es serializable/simple):
    self._crop_box: tuple[int, int, int, int] | None  # (left, top, right, bottom) en coordenadas de la imagen original
    self._crop_mode_active: bool  # armado esperando el primer arrastre, antes de que exista _crop_box
```

No se agregan claves a `config.json`: el recorte es estado transitorio de la sesión de OCR de imágenes, no persistido.

## Implementation plan

1. **`model/image_tiling.py`: extraer `prepare_tiles_from_image`.** Mover la lógica de `prepare_tiles` (todo lo que hace tras `Image.open`) a la nueva función `prepare_tiles_from_image(image)`. `prepare_tiles(image_path)` pasa a ser `return prepare_tiles_from_image(Image.open(image_path))`.
   Prueba manual: `python -c "from model.image_tiling import prepare_tiles; print(len(prepare_tiles('alguna_imagen_grande.png')))"` devuelve el mismo resultado que antes del refactor (sin cambios de comportamiento).

2. **`model/ocr_model.py`: nueva `transcribe_cropped_image()`.** Implementar usando `prepare_tiles_from_image` + `transcribe_image_variants` por tile, mismo patrón que el cuerpo de `transcribe_large_image` pero recibiendo la imagen ya en memoria.
   Prueba manual: `python -c "from PIL import Image; from model.ocr_model import transcribe_cropped_image; img = Image.open('alguna_imagen.png').crop((0,0,300,150)); print(transcribe_cropped_image(img, 'spa+eng', None))"` devuelve texto sin error.

3. **`view/ocr_view.py`: botón único de recorte y `QRubberBand`.** Agregar `crop_button` (`checkable`, texto inicial "Activar recorte"), envuelto en `QVBoxLayout` con `QLabel("")` espaciador, agregado a `left_toolbar` junto a `open_button`. Instanciar `QRubberBand(QRubberBand.Rectangle, self.preview_label)`, oculto por defecto. Señal única `crop_toggled` conectada al `clicked` del botón. Métodos `update_crop_button(has_crop: bool, armed: bool)` (setea texto "Quitar recorte"/"Activar recorte" y estado `checked`), `show_crop_rect(rect: QRect)` (posiciona y muestra el `QRubberBand`), `hide_crop_rect()`.
   Prueba manual: instanciar `OcrView` sola, confirmar que aparece el botón alineado con "Abrir imagen" con texto inicial "Activar recorte", y que los setters nuevos no explotan al llamarlos con datos de prueba.

4. **`view/metro_style.py`: estilos del botón y el `QRubberBand`.** Confirmar que `crop_button` hereda el estilo de `QPushButton` ya definido y que su selector `#cropButton:checked` se lee bien tanto para "armado" como para "con recorte" (mismo estado visual `checked`); agregar regla para `QRubberBand` con el color de acento `rgb(42,130,218)`, en ambos temas.
   Prueba manual: alternar tema en Configuración, confirmar que el botón y el rectángulo de selección se ven legibles y consistentes en claro/oscuro.

5. **`controller/ocr_controller.py`: estado y ciclo de recorte.** Agregar `self._crop_box: tuple[int, int, int, int] | None = None` y `self._crop_mode_active = False`. Conectar `crop_toggled` → `on_crop_toggled`: si `self._crop_box` no es `None`, lo limpia (`_crop_box = None`, `_crop_mode_active = False`, `hide_crop_rect()`, `update_crop_button(has_crop=False, armed=False)`); si es `None`, alterna `self._crop_mode_active` y refleja el armado (`update_crop_button(has_crop=False, armed=self._crop_mode_active)`). Extender el `eventFilter` existente sobre `preview_label` para capturar `MouseButtonPress`/`MouseMove`/`MouseButtonRelease` cuando `self._crop_mode_active` **o** `self._crop_box is not None` (permite redefinir arrastrando de nuevo sin pasar por el botón): en press guarda el punto inicial y muestra el `QRubberBand` en tiempo real durante move; en release, si el rectángulo final (en coordenadas de `preview_label`) supera un umbral mínimo constante (ej. 10x10px), mapea las coordenadas de preview a coordenadas de la imagen original (revirtiendo el `ImageOps.contain` de `_render_preview`: escala y offset de letterboxing), guarda `self._crop_box`, desactiva `self._crop_mode_active` y actualiza el botón a "Quitar recorte" (`update_crop_button(has_crop=True, armed=False)`); si no supera el umbral, conserva el recorte previo redibujándolo (si ya existía `_crop_box`) o cancela el armado (`_crop_mode_active = False`, `hide_crop_rect()`, `update_crop_button(has_crop=False, armed=False)`) si no existía. En `on_open_image()`, resetear `self._crop_box = None` y `self._crop_mode_active = False`, llamar `view.hide_crop_rect()` + `view.update_crop_button(has_crop=False, armed=False)` antes de cargar la imagen nueva. En `on_transcribe()`/`_start_transcription()`, si `self._crop_box` no es `None`, recortar `self._preview_source.crop(self._crop_box)` y pasarlo como `cropped_image` al `TranscriptionWorker`; si es `None`, comportamiento actual sin cambios. Además, `_render_preview()` (llamado en cada resize del `preview_label`) debe recalcular y reposicionar el `QRubberBand` visible vía `show_crop_rect` cuando `self._crop_box` está activo, para que no quede desalineado tras un resize de la ventana.
   Prueba manual: cargar una imagen, clickear "Activar recorte", arrastrar un rectángulo sobre un fragmento de texto, confirmar que queda dibujado y el botón pasa a "Quitar recorte"; sin tocar el botón, arrastrar otra región y confirmar que redefine el recorte; clickear "Transcribir" y confirmar que el resultado corresponde solo al fragmento seleccionado (no a la imagen completa); clickear "Quitar recorte" y confirmar que "Transcribir" vuelve a procesar la imagen completa y el botón vuelve a "Activar recorte"; repetir un arrastre menor al umbral y confirmar que no activa ningún recorte nuevo (y conserva el previo si había uno); cargar una imagen nueva con un recorte activo y confirmar que se limpia solo; redimensionar la ventana con un recorte activo y confirmar que el rectángulo se reposiciona junto con la preview.

6. **Verificación end-to-end.** Recorrido manual completo: abrir imagen grande (que dispare tiling) y otra chica, activar recorte sobre cada una, transcribir el recorte, quitar el recorte y transcribir la imagen completa, alternar tema, y confirmar que el flujo de "OCR en vivo" (spec 08-09) sigue funcionando sin regresiones. Revisión de imports rotos.
   Prueba: recorrido manual + revisión de imports rotos.

## Acceptance criteria

- [x] `OcrView` muestra un único botón de recorte alineado con "Abrir imagen"; arranca con texto "Activar recorte".
- [x] Clickear "Activar recorte" habilita el modo de selección (botón resaltado); el siguiente arrastre sobre la vista previa dibuja un rectángulo en tiempo real.
- [x] Al soltar el mouse tras un arrastre válido (por encima del umbral mínimo), el rectángulo queda dibujado de forma persistente sobre la vista previa y el botón pasa a mostrar "Quitar recorte".
- [x] Con un recorte ya dibujado, arrastrar de nuevo sobre la vista previa (sin clickear ningún botón) redefine la región seleccionada.
- [x] Un arrastre menor al umbral mínimo no activa ningún recorte nuevo ni deja rectángulo dibujado; si ya existía un recorte, se conserva sin cambios.
- [x] Con un recorte activo, clickear "Transcribir" procesa solo la región seleccionada (en resolución original, no la preview reescalada) y el resultado corresponde a ese fragmento.
- [x] Sin recorte activo, "Transcribir" sigue procesando la imagen completa exactamente igual que antes de esta spec (sin regresiones para imágenes grandes con tiling).
- [x] Clickear "Quitar recorte" oculta el rectángulo, el botón vuelve a mostrar "Activar recorte", y la siguiente transcripción vuelve a usar la imagen completa.
- [x] Cargar una imagen nueva con "Abrir imagen" limpia automáticamente cualquier recorte activo (rectángulo oculto, botón vuelto a "Activar recorte").
- [x] El recorte funciona tanto sobre imágenes que requieren tiling (spec 02) como sobre imágenes chicas, aplicando preprocesamiento multi-variante (spec 03) en ambos casos.
- [x] El flujo de "OCR en vivo" (specs 08-09) sigue funcionando sin regresiones.
- [x] MVC respetado: `view/ocr_view.py` no llama a `pytesseract` ni contiene lógica de mapeo de coordenadas; la lógica de recorte y mapeo vive en `OcrController`; `model/image_tiling.py` y `model/ocr_model.py` no importan PySide6.
- [x] No hay texto ilegible ni rectángulo de recorte con bajo contraste bajo ningún tema (claro/oscuro).

## Decisions

- **Sí:** botón explícito "Activar recorte" en vez de permitir arrastrar directamente sobre la preview en cualquier momento (mientras no existe recorte). Evita recortes accidentales al interactuar con la imagen, siguiendo el mismo patrón ya validado en spec 08 para el overlay de OCR en vivo.
- **Sí:** un único botón que fusiona "Activar recorte"/"Quitar recorte" en vez de dos controles separados, cambiando de texto según haya o no una región seleccionada. Reduce a un solo control visual el ciclo completo (armar → quitar), sin dos botones que puedan quedar en estados inconsistentes entre sí.
- **Sí:** una vez que existe un recorte, arrastrar de nuevo sobre la vista previa lo redefine directamente, sin pasar de nuevo por "Quitar recorte" + "Activar recorte". El caso de uso típico es iterar la región varias veces antes de transcribir; forzar el ciclo completo por cada ajuste era fricción innecesaria (cambio respecto a la decisión original de "un solo arrastre por activación").
- **Sí:** el rectángulo de selección queda dibujado de forma persistente tras soltar el mouse, como feedback visual de qué se va a transcribir, en vez de desaparecer y depender solo del estado interno del botón.
- **Sí:** el recorte solo afecta la transcripción; la vista previa sigue mostrando siempre la imagen completa con el rectángulo superpuesto, en vez de reemplazar la preview por el fragmento recortado. Mantiene contexto visual de dónde está ubicada la región dentro de la imagen completa.
- **Sí:** el recorte se aplica sobre `self._preview_source` (imagen en resolución original ya cargada en memoria) mapeando coordenadas desde la preview reescalada, en vez de releer el archivo desde disco. Evita I/O redundante y mantiene consistencia con el mismo objeto que ya usa `_render_preview`.
- **Sí:** reutilizar tiling + preprocesamiento (`prepare_tiles_from_image` + `transcribe_image_variants`) para el recorte, igual que la imagen completa, en vez de una ruta simplificada sin tiling. Si el usuario recorta una región grande de una imagen de alta resolución, sigue necesitando el mismo tratamiento que ya evita fallos de Tesseract con imágenes grandes (spec 02).
- **Sí:** usar `QRubberBand` nativo de Qt en vez de un overlay custom con `paintEvent` propio (a diferencia de `ScreenOverlay` en spec 08, que sí necesitaba ser una ventana top-level independiente para capturar pantalla). Acá el rectángulo vive dentro de la misma ventana sobre un `QLabel`, caso de uso estándar para el que `QRubberBand` ya está diseñado.
- **Sí:** umbral mínimo de tamaño de arrastre para descartar clicks/arrastres accidentales, en vez de aceptar cualquier área mayor a cero.
- **No:** permitir mover o redimensionar el rectángulo ya dibujado. Alcanza con "Quitar recorte" + volver a activar y redibujar; agregar handles de redimensión (como los de `ScreenOverlay`) sería complejidad extra no pedida para este caso de uso puntual.
- **No:** persistir el recorte entre imágenes, navegaciones o sesiones. Es estado transitorio de la sesión de OCR de imágenes actual, sin necesidad planteada de recordarlo.
- **No:** aplicar esta feature a "OCR en vivo". El overlay de spec 08 ya cumple el rol de "seleccionar una región" para ese flujo; agregarlo ahí sería redundante.
- **Sí:** por defecto, las pruebas manuales de cada paso del plan de implementación las ejecuta el usuario, no el asistente; el asistente solo verifica por otros medios (lectura de código, `grep`, chequeo de imports) cuando el usuario no pueda evaluar el cambio corriendo el proyecto. Este es el default heredado de spec 09, no una prohibición absoluta.

## Risks

| Risk | Mitigation |
|---|---|
| El mapeo de coordenadas entre la preview reescalada (con letterboxing por `ImageOps.contain`) y la imagen original puede desalinearse si no se calcula bien el offset/escala, produciendo un recorte desplazado respecto a lo que el usuario ve. | El paso 5 exige revertir explícitamente la transformación de `_render_preview` (mismo factor de escala y offset de centrado); se verifica arrastrando sobre un fragmento de texto conocido y confirmando que el resultado transcripto corresponde exactamente a ese fragmento. |
| Redimensionar la ventana de `preview_label` después de dibujar el rectángulo persistente (el `eventFilter` ya dispara `_render_preview` en cada resize) puede dejar el `QRubberBand` dibujado en una posición vieja que ya no corresponde a la imagen reescalada. | El paso 5 recalcula y reposiciona el `QRubberBand` visible (vía `show_crop_rect`) cada vez que `_render_preview` se ejecuta con un `self._crop_box` activo, no solo al soltar el mouse. |
| Si el usuario arrastra fuera de los límites de `preview_label` (mouse sale del widget durante el drag), el rectángulo final podría incluir coordenadas fuera de la imagen real. | El paso 5 debe clampear las coordenadas del rectángulo al área visible de la imagen dentro de `preview_label` antes de mapear a la imagen original. |
| Reutilizar tiling completo (`prepare_tiles_from_image`) sobre un recorte que ya es chico agrega overhead innecesario si el recorte nunca supera `MAX_DIMENSION`. | No es un problema real en la práctica: `prepare_tiles_from_image` ya devuelve la imagen sin modificar cuando entra dentro de `MAX_DIMENSION` en ambos lados (mismo camino rápido que hoy usa `transcribe_large_image` para imágenes chicas), así que el costo extra es despreciable. |
