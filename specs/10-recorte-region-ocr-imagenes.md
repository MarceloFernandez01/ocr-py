# SPEC 10 — Recorte de región antes de transcribir en OCR de imágenes

> **Status:** Aceptar
> **Depends on:** `specs/01-mvp-ocr-tesseract-tkinter.md`, `specs/02-ocr-imagenes-grandes.md`, `specs/03-preprocesamiento-ocr.md`, `specs/09-live-ocr-boton-iniciar-transcripcion.md`
> **Date:** 2026-07-13
> **Objective:** Permitir seleccionar arrastrando un rectángulo sobre la vista previa de `OcrView` para que "Transcribir" procese solo esa región de la imagen en vez de la imagen completa.

## Scope

**In:**

- **`view/ocr_view.py`**: nuevos botones `crop_button` ("Activar recorte") y `clear_crop_button` ("Quitar recorte"), este último deshabilitado por defecto. Ambos envueltos en `QVBoxLayout` con `QLabel("")` espaciador, siguiendo la convención de alineación de spec 09, ubicados en `left_toolbar` junto a `open_button`. Nuevas señales `crop_activated` (al clickear "Activar recorte") y `crop_cleared` (al clickear "Quitar recorte"). Un `QRubberBand` se instala sobre `preview_label` para dibujar la selección durante el arrastre y queda visible (congelado) tras soltar el mouse, mostrando el área que se transcribirá. Nuevos métodos: `enable_clear_crop_button()`, `disable_clear_crop_button()`, `set_crop_mode_active(active: bool)` (feedback visual de que el próximo arrastre define el recorte), `show_crop_rect(rect: QRect)`, `hide_crop_rect()`.
- **`controller/ocr_controller.py`**: nuevo estado `self._crop_box: tuple[int, int, int, int] | None` (coordenadas en la imagen original, no en la preview). Maneja el ciclo: click en "Activar recorte" → arma modo recorte (`set_crop_mode_active(True)`) → instala/activa manejo de mouse press/move/release sobre `preview_label` vía `eventFilter` (ya existente para el resize) → al soltar, si el rectángulo supera el umbral mínimo, mapea las coordenadas de la preview (que puede tener letterboxing por `ImageOps.contain`) a coordenadas de la imagen original, guarda `self._crop_box`, dibuja el rectángulo persistente (mapeado de vuelta a coordenadas de preview) y habilita `clear_crop_button`; si no supera el umbral, descarta el intento sin activar recorte. `set_crop_mode_active(False)` se llama automáticamente al terminar el arrastre (un solo arrastre por activación). Click en "Quitar recorte" limpia `self._crop_box`, oculta el rectángulo y deshabilita el propio botón. `on_open_image()` resetea `self._crop_box` a `None` y oculta el rectángulo al cargar una imagen nueva. `on_transcribe()` recorta `self._preview_source` (imagen en resolución original) con `self._crop_box` si está seteado antes de lanzar `TranscriptionWorker`.
- **`model/image_tiling.py`**: se extrae `prepare_tiles_from_image(image: Image.Image) -> list[Image.Image]` con la lógica actual de `prepare_tiles`, y `prepare_tiles(image_path)` pasa a abrir la imagen y delegar en la nueva función. Sin cambio de comportamiento para los llamadores existentes.
- **`model/ocr_model.py`**: nueva función pública `transcribe_cropped_image(image: Image.Image, language_code: str, tesseract_path: str | None) -> str`, análoga a `transcribe_large_image` pero recibiendo una `PIL.Image` ya recortada en memoria en vez de una ruta: aplica `prepare_tiles_from_image` + `transcribe_image_variants` por tile igual que `transcribe_large_image`.
- **`controller/ocr_controller.py`**: `TranscriptionWorker` gana un parámetro opcional `image: Image.Image | None` — si viene seteado, el worker llama a `transcribe_cropped_image(image, ...)` en vez de `transcribe_large_image(image_path, ...)`.
- **`view/metro_style.py`**: estilos para `crop_button`/`clear_crop_button` (mismo patrón que otros `QPushButton`) y para el `QRubberBand` (color de acento, coherente con el borde de `ScreenOverlay` de spec 08), en ambos temas.

**Out:**

- No se toca `LiveOcrView` ni `ScreenOverlay`; el recorte de región en OCR en vivo ya está cubierto por el overlay (spec 08) y queda fuera de alcance.
- No se persiste el recorte entre imágenes, navegaciones de sidebar, ni sesiones.
- No se permite mover/redimensionar el rectángulo ya dibujado (solo redibujar uno nuevo activando "Activar recorte" de nuevo, o quitarlo con "Quitar recorte").
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
```

No se agregan claves a `config.json`: el recorte es estado transitorio de la sesión de OCR de imágenes, no persistido.

## Implementation plan

1. **`model/image_tiling.py`: extraer `prepare_tiles_from_image`.** Mover la lógica de `prepare_tiles` (todo lo que hace tras `Image.open`) a la nueva función `prepare_tiles_from_image(image)`. `prepare_tiles(image_path)` pasa a ser `return prepare_tiles_from_image(Image.open(image_path))`.
   Prueba manual: `python -c "from model.image_tiling import prepare_tiles; print(len(prepare_tiles('alguna_imagen_grande.png')))"` devuelve el mismo resultado que antes del refactor (sin cambios de comportamiento).

2. **`model/ocr_model.py`: nueva `transcribe_cropped_image()`.** Implementar usando `prepare_tiles_from_image` + `transcribe_image_variants` por tile, mismo patrón que el cuerpo de `transcribe_large_image` pero recibiendo la imagen ya en memoria.
   Prueba manual: `python -c "from PIL import Image; from model.ocr_model import transcribe_cropped_image; img = Image.open('alguna_imagen.png').crop((0,0,300,150)); print(transcribe_cropped_image(img, 'spa+eng', None))"` devuelve texto sin error.

3. **`view/ocr_view.py`: botones de recorte y `QRubberBand`.** Agregar `crop_button` ("Activar recorte") y `clear_crop_button` ("Quitar recorte", `setEnabled(False)` inicial), envueltos en `QVBoxLayout` con `QLabel("")` espaciador, agregados a `left_toolbar` junto a `open_button`. Instanciar `QRubberBand(QRubberBand.Rectangle, self.preview_label)`, oculto por defecto. Señales `crop_activated`/`crop_cleared` conectadas a los `clicked` respectivos. Métodos `enable_clear_crop_button()`, `disable_clear_crop_button()`, `set_crop_mode_active(active: bool)` (cambia `crop_button` a estado `checked`/estilo activo mientras se espera el arrastre), `show_crop_rect(rect: QRect)` (posiciona y muestra el `QRubberBand`), `hide_crop_rect()`.
   Prueba manual: instanciar `OcrView` sola, confirmar que aparecen los dos botones nuevos alineados con "Abrir imagen", que "Quitar recorte" arranca deshabilitado, y que los setters nuevos no explotan al llamarlos con datos de prueba.

4. **`view/metro_style.py`: estilos de los botones nuevos y el `QRubberBand`.** Confirmar que `crop_button`/`clear_crop_button` heredan el estilo de `QPushButton` ya definido (agregar selector específico solo si `crop_button` necesita diferenciarse visualmente en su estado "activo"); agregar regla para `QRubberBand` con el color de acento `rgb(42,130,218)`, en ambos temas.
   Prueba manual: alternar tema en Configuración, confirmar que los botones y el rectángulo de selección se ven legibles y consistentes en claro/oscuro.

5. **`controller/ocr_controller.py`: estado y ciclo de recorte.** Agregar `self._crop_box: tuple[int, int, int, int] | None = None` y `self._crop_mode_active = False`. Conectar `crop_activated` → activa `self._crop_mode_active = True` y `view.set_crop_mode_active(True)`. Extender el `eventFilter` existente sobre `preview_label` para capturar `MouseButtonPress`/`MouseMove`/`MouseButtonRelease` cuando `self._crop_mode_active` es `True`: en press guarda el punto inicial y muestra el `QRubberBand` en tiempo real durante move; en release, si el rectángulo final (en coordenadas de `preview_label`) supera un umbral mínimo constante (ej. 10x10px), mapea las coordenadas de preview a coordenadas de la imagen original (revirtiendo el `ImageOps.contain` de `_render_preview`: escala y offset de letterboxing), guarda `self._crop_box`, llama a `view.show_crop_rect(...)` con el rect final y `view.enable_clear_crop_button()`; si no supera el umbral, no activa ningún recorte. En ambos casos (supere o no el umbral) desactiva `self._crop_mode_active = False` y `view.set_crop_mode_active(False)`. Conectar `crop_cleared` → limpia `self._crop_box`, `view.hide_crop_rect()`, `view.disable_clear_crop_button()`. En `on_open_image()`, resetear `self._crop_box = None` y llamar `view.hide_crop_rect()` + `view.disable_clear_crop_button()` antes de cargar la imagen nueva. En `on_transcribe()`/`_start_transcription()`, si `self._crop_box` no es `None`, recortar `self._preview_source.crop(self._crop_box)` y pasarlo como `cropped_image` al `TranscriptionWorker`; si es `None`, comportamiento actual sin cambios. Además, `_render_preview()` (llamado en cada resize del `preview_label`) debe recalcular y reposicionar el `QRubberBand` visible vía `show_crop_rect` cuando `self._crop_box` está activo, para que no quede desalineado tras un resize de la ventana.
   Prueba manual: cargar una imagen, clickear "Activar recorte", arrastrar un rectángulo sobre un fragmento de texto, confirmar que queda dibujado y "Quitar recorte" se habilita; clickear "Transcribir" y confirmar que el resultado corresponde solo al fragmento seleccionado (no a la imagen completa); clickear "Quitar recorte" y confirmar que "Transcribir" vuelve a procesar la imagen completa; repetir un arrastre menor al umbral y confirmar que no activa ningún recorte; cargar una imagen nueva con un recorte activo y confirmar que se limpia solo; redimensionar la ventana con un recorte activo y confirmar que el rectángulo se reposiciona junto con la preview.

6. **Verificación end-to-end.** Recorrido manual completo: abrir imagen grande (que dispare tiling) y otra chica, activar recorte sobre cada una, transcribir el recorte, quitar el recorte y transcribir la imagen completa, alternar tema, y confirmar que el flujo de "OCR en vivo" (spec 08-09) sigue funcionando sin regresiones. Revisión de imports rotos.
   Prueba: recorrido manual + revisión de imports rotos.

## Acceptance criteria

- [ ] `OcrView` muestra los botones "Activar recorte" y "Quitar recorte" alineados con "Abrir imagen"; "Quitar recorte" arranca deshabilitado.
- [ ] Clickear "Activar recorte" habilita el modo de selección; el siguiente arrastre sobre la vista previa dibuja un rectángulo en tiempo real.
- [ ] Al soltar el mouse tras un arrastre válido (por encima del umbral mínimo), el rectángulo queda dibujado de forma persistente sobre la vista previa, "Quitar recorte" se habilita, y el modo de selección se desactiva automáticamente (no hace falta volver a clickear "Activar recorte" para hacer click normal en la vista).
- [ ] Un arrastre menor al umbral mínimo no activa ningún recorte ni deja rectángulo dibujado.
- [ ] Con un recorte activo, clickear "Transcribir" procesa solo la región seleccionada (en resolución original, no la preview reescalada) y el resultado corresponde a ese fragmento.
- [ ] Sin recorte activo, "Transcribir" sigue procesando la imagen completa exactamente igual que antes de esta spec (sin regresiones para imágenes grandes con tiling).
- [ ] Clickear "Quitar recorte" oculta el rectángulo, deshabilita el propio botón, y la siguiente transcripción vuelve a usar la imagen completa.
- [ ] Cargar una imagen nueva con "Abrir imagen" limpia automáticamente cualquier recorte activo (rectángulo oculto, botón "Quitar recorte" deshabilitado).
- [ ] El recorte funciona tanto sobre imágenes que requieren tiling (spec 02) como sobre imágenes chicas, aplicando preprocesamiento multi-variante (spec 03) en ambos casos.
- [ ] El flujo de "OCR en vivo" (specs 08-09) sigue funcionando sin regresiones.
- [ ] MVC respetado: `view/ocr_view.py` no llama a `pytesseract` ni contiene lógica de mapeo de coordenadas; la lógica de recorte y mapeo vive en `OcrController`; `model/image_tiling.py` y `model/ocr_model.py` no importan PySide6.
- [ ] No hay texto ilegible ni rectángulo de recorte con bajo contraste bajo ningún tema (claro/oscuro).

## Decisions

- **Sí:** botón explícito "Activar recorte" en vez de permitir arrastrar directamente sobre la preview en cualquier momento. Evita recortes accidentales al interactuar con la imagen, siguiendo el mismo patrón ya validado en spec 08 para el overlay de OCR en vivo.
- **Sí:** el modo de recorte se autodesactiva tras un solo arrastre (no es un toggle persistente). El caso de uso típico es "seleccionar una región y transcribir", no redibujar repetidamente sin releer el estado del botón.
- **Sí:** el rectángulo de selección queda dibujado de forma persistente tras soltar el mouse, como feedback visual de qué se va a transcribir, en vez de desaparecer y depender solo del estado interno del botón "Quitar recorte".
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
