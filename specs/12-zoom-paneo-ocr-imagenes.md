# SPEC 12 — Zoom y paneo en la vista previa de OCR de imágenes

> **Status:** Implementado
> **Depends on:** `specs/03-preprocesamiento-ocr.md`, `specs/10-recorte-region-ocr-imagenes.md`
> **Date:** 2026-07-18
> **Objective:** Agregar zoom con la rueda del mouse (centrado en el cursor) y paneo con click derecho a la vista previa de `OcrView`, y simplificar el recorte de spec 10 para que el click izquierdo seleccione el área directamente sin pasar por un botón de armado.

## Scope

**In:**

- **`view/ocr_view.py`**: nuevo `reset_zoom_button` ("Restablecer zoom"), envuelto en `QVBoxLayout` con `QLabel("")` espaciador, agregado a `left_toolbar` junto a `open_button` y `crop_button`. `crop_button` deja de ser `checkable`: pasa a ser un botón simple, deshabilitado por defecto, texto fijo "Quitar recorte", habilitado solo cuando hay una región seleccionada. Nuevo `zoom_label` flotante (`QLabel`, hijo de `preview_label`, posicionado en la esquina inferior derecha, fondo semitransparente), oculto por defecto, para mostrar el porcentaje de zoom actual. `preview_label` pasa a tener `setContextMenuPolicy(Qt.NoContextMenu)` para que el click derecho no dispare el menú contextual nativo. Método `update_crop_button(has_crop: bool)` (reemplaza al `update_crop_button(has_crop, armed)` de spec 10, sin el parámetro `armed`). Métodos nuevos `set_zoom_label(text: str)` (setea texto y muestra la etiqueta), `hide_zoom_label()`, y `position_zoom_label()` (reposiciona la etiqueta flotante en la esquina inferior derecha de `preview_label` usando su tamaño actual, a llamar tras cada resize/render).
- **`controller/ocr_controller.py`**: nuevo estado de zoom/paneo — `self._zoom: float` (1.0 a 5.0), `self._zoom_center: tuple[float, float] | None` (punto en coordenadas de la imagen original alrededor del cual se arma la región visible), `self._pan_drag_start` / `self._pan_start_center` (para el arrastre con click derecho). Se elimina `self._crop_mode_active` (ya no existe el "armado" del recorte de spec 10). El `eventFilter` sobre `preview_label` se extiende para manejar: `QEvent.Wheel` (zoom centrado en el cursor), `QEvent.MouseButtonPress/Move/Release` con botón derecho (paneo), y el arrastre con botón izquierdo para recorte pasa a estar **siempre activo** sobre `preview_label` (ya no depende de `_crop_mode_active` ni de que exista `_crop_box`). `_render_preview()` calcula la "región visible" de la imagen original según `_zoom`/`_zoom_center` (clampeada a los bordes de la imagen), recorta `self._preview_source` a esa región y la reescala para llenar exactamente el mismo recuadro (`_preview_image_rect`) que ya se usa hoy para el letterboxing en zoom 1x — el recuadro (offset y tamaño dentro de `preview_label`) no cambia con el zoom, solo cambia qué porción de la imagen se dibuja dentro de él. `_map_point_to_original()` y `_redraw_crop_rect()` se actualizan para mapear contra la región visible actual (no siempre contra la imagen completa como en spec 10), de forma que el recorte siga siendo preciso con cualquier nivel de zoom/paneo. El botón de recorte (`crop_toggled`, sin renombrar la señal) pasa a significar únicamente "quitar recorte" (ya no alterna armado).
- **`view/metro_style.py`**: estilo para `reset_zoom_button` (mismo patrón que otros `QPushButton`), `crop_button` deshabilitado/habilitado (ya no necesita el selector `:checked` de "armado", solo `:disabled` vs. estado normal), y `zoom_label` (fondo semitransparente oscuro, texto claro, esquinas redondeadas, legible sobre cualquier imagen de fondo), en ambos temas.

**Out:**

- No se toca `LiveOcrView` ni `ScreenOverlay`; zoom y paneo quedan limitados a `OcrView`.
- El recuadro donde se dibuja la imagen (letterbox) no cambia de tamaño ni posición con el zoom; solo cambia el contenido recortado que se muestra dentro de él. No se implementa un modo "sin letterbox" que expanda la imagen para llenar todo `preview_label`.
- El paneo no tiene efecto en zoom 1x (imagen ajustada): la región visible clampea automáticamente para no permitir mover la imagen cuando ya está completa a la vista.
- No se persiste el nivel de zoom ni el paneo entre imágenes, navegaciones de sidebar ni sesiones: cargar una imagen nueva resetea zoom a 1x y el centro al medio de la imagen. Quitar el recorte (spec 10) **no** resetea el zoom/paneo.
- No se agregan atajos de teclado para zoom (+/-) ni doble-click para resetear; el único mecanismo de reset es el botón "Restablecer zoom".
- No se agrega ningún control para "mover/redimensionar" el rectángulo de recorte ya dibujado con handles (se mantiene la decisión de spec 10: solo redefinirlo arrastrando de nuevo o quitándolo con el botón).

## Data model

```python
# controller/ocr_controller.py (ampliación)

ZOOM_MIN = 1.0
ZOOM_MAX = 5.0
ZOOM_STEP = 1.25
"""Factor de zoom relativo a la imagen ajustada a `preview_label` (1.0 = fit
actual, igual que el comportamiento previo a esta spec). Cada notch de rueda
multiplica o divide `_zoom` por `ZOOM_STEP`, clampeado a [ZOOM_MIN, ZOOM_MAX]."""


class OcrController(QObject):
    # Nuevo estado en memoria (no persistido):
    self._zoom: float  # arranca en 1.0, rango [ZOOM_MIN, ZOOM_MAX]
    self._zoom_center: tuple[float, float] | None
    # Punto (x, y) en coordenadas de la imagen ORIGINAL alrededor del cual se
    # arma la región visible actual. None hasta que se carga una imagen;
    # se inicializa al centro de la imagen en on_open_image().

    self._pan_drag_start: QPointF | None
    # Punto de `preview_label` donde arrancó el arrastre con click derecho.

    self._pan_start_center: tuple[float, float] | None
    # Copia de `_zoom_center` al momento de arrancar el paneo, para calcular
    # el desplazamiento total del arrastre (no incremental por evento).

    # Estado que se ELIMINA de spec 10:
    # self._crop_mode_active  (ya no existe "armado" del recorte)
```

```python
# controller/ocr_controller.py (ampliación)

def _current_visible_region(self) -> tuple[float, float, float, float]:
    """Calcula (left, top, right, bottom) en coordenadas de la imagen original
    que representan la región actualmente visible en `preview_label`, según
    `self._zoom` y `self._zoom_center`. El tamaño de la región es
    (original_width / zoom, original_height / zoom); el centro se clampea
    para que la región completa quede dentro de los límites de la imagen
    (mismo mecanismo que ya clampea el recorte, aplicado acá a la cámara)."""
```

Sin cambios en `model/` ni en `config.json`: igual que el recorte de spec 10, el zoom y el paneo son estado transitorio de la sesión de OCR de imágenes, no persistido.

## Implementation plan

1. **`view/ocr_view.py`: `reset_zoom_button`, `zoom_label` flotante, y simplificación de `crop_button`.** Agregar `reset_zoom_button` ("Restablecer zoom"), envuelto en `QVBoxLayout` con `QLabel("")` espaciador, agregado a `left_toolbar` junto a `crop_button`. Cambiar `crop_button` a `setCheckable(False)`, `setEnabled(False)` por defecto, texto fijo "Quitar recorte". Reemplazar `update_crop_button(has_crop, armed)` por `update_crop_button(has_crop: bool)` (solo habilita/deshabilita). Crear `zoom_label` como hijo de `preview_label` (no del layout), con fondo semitransparente y oculto por defecto; agregar `set_zoom_label(text: str)`, `hide_zoom_label()` y `position_zoom_label()` (calcula y aplica la geometría en la esquina inferior derecha de `preview_label` usando su tamaño actual). Setear `preview_label.setContextMenuPolicy(Qt.NoContextMenu)`.
   Prueba manual: instanciar `OcrView` sola, confirmar que aparece "Restablecer zoom" alineado con los otros botones de la toolbar izquierda, que `crop_button` arranca deshabilitado con texto "Quitar recorte", y que los métodos nuevos no explotan al llamarlos con datos de prueba.

2. **`view/metro_style.py`: estilos nuevos.** Agregar regla para `reset_zoom_button` (mismo patrón que otros `QPushButton`), actualizar el selector de `crop_button` para reflejar solo estado habilitado/deshabilitado (eliminar el selector `:checked` de "armado" de spec 10), y agregar regla para `zoom_label` (fondo semitransparente oscuro fijo, texto claro, esquinas redondeadas) en ambos temas.
   Prueba manual: alternar tema en Configuración, confirmar legibilidad de `reset_zoom_button`, `crop_button` (habilitado/deshabilitado) y `zoom_label` sobre distintas imágenes de fondo.

3. **`controller/ocr_controller.py`: estado de zoom/paneo y `_current_visible_region()`.** Agregar `ZOOM_MIN`, `ZOOM_MAX`, `ZOOM_STEP` como constantes de módulo. Agregar `self._zoom = 1.0`, `self._zoom_center = None`, `self._pan_drag_start = None`, `self._pan_start_center = None`. Eliminar `self._crop_mode_active`. Implementar `_current_visible_region()` según el data model. En `on_open_image()`, resetear `self._zoom = 1.0` y `self._zoom_center = (width / 2, height / 2)` de la imagen recién cargada.
   Prueba manual: cargar una imagen y confirmar (con un print temporal o el debugger) que `_current_visible_region()` devuelve los límites completos de la imagen en zoom 1.0.

4. **`controller/ocr_controller.py`: `_render_preview()` usa la región visible.** Modificar `_render_preview()` para: calcular `_current_visible_region()`, recortar `self._preview_source` a esa región (coordenadas enteras), reescalar el recorte para llenar exactamente `_preview_image_rect` (el mismo recuadro fijo de letterbox que ya se calcula al ajustar la imagen completa en zoom 1.0), y dibujar ese resultado. Actualizar `_map_point_to_original()` y `_redraw_crop_rect()` para mapear contra la región visible actual en vez de contra la imagen completa. Después de dibujar, llamar `view.position_zoom_label()` y actualizar su texto/visibilidad (`set_zoom_label(f"{int(self._zoom * 100)}%")` si `self._zoom != 1.0`, `hide_zoom_label()` si `self._zoom == 1.0`).
   Prueba manual: con `self._zoom` forzado a 2.0 y `_zoom_center` al centro de la imagen (vía debugger o un botón temporal), confirmar que la vista previa muestra un recorte central ampliado de la imagen dentro del mismo recuadro que antes mostraba la imagen completa.

5. **`controller/ocr_controller.py`: zoom con la rueda del mouse.** En el `eventFilter`, capturar `QEvent.Wheel` sobre `preview_label`: si el punto del cursor cae fuera de `_preview_image_rect`, ignorar; si no, calcular el punto de la imagen original bajo el cursor (vía `_map_point_to_original`, usando la región visible **antes** de cambiar el zoom), aplicar `ZOOM_STEP` (multiplicar si `angleDelta().y() > 0`, dividir si `< 0`) clampeado a `[ZOOM_MIN, ZOOM_MAX]`, y recalcular `self._zoom_center` para que ese mismo punto de imagen quede bajo el cursor tras el cambio de zoom (misma región visible nueva, centro ajustado). Llamar `_render_preview()`.
   Prueba manual: cargar una imagen, girar la rueda hacia arriba sobre un fragmento de texto específico, confirmar que ese fragmento queda centrado bajo el cursor y agrandado; girar hacia abajo hasta volver a 100% y confirmar que vuelve exactamente a la imagen completa ajustada.

6. **`controller/ocr_controller.py`: paneo con click derecho.** En el `eventFilter`, capturar `QEvent.MouseButtonPress` con `event.button() == Qt.RightButton` sobre `preview_label`: guardar `self._pan_drag_start = event.position()` y `self._pan_start_center = self._zoom_center`. En `QEvent.MouseMove` con `self._pan_drag_start` seteado: calcular el delta en píxeles de `preview_label` desde el inicio del arrastre, convertirlo a delta en coordenadas de imagen original usando la escala actual (`región_visible.width() / _preview_image_rect.width()`), y setear `self._zoom_center` como `_pan_start_center` menos ese delta (arrastrar a la derecha mueve el contenido a la derecha, o sea la cámara se mueve a la izquierda), clampeado por `_current_visible_region()`. En `QEvent.MouseButtonRelease` con botón derecho, limpiar `self._pan_drag_start`/`self._pan_start_center`. Llamar `_render_preview()` en cada move. Todos estos casos devuelven `True` del `eventFilter` para no propagar el evento (evita que dispare selección de texto u otros efectos nativos).
   Prueba manual: con zoom > 100%, arrastrar con click derecho en distintas direcciones y confirmar que la imagen se desplaza de forma natural (arrastrar hacia la izquierda revela contenido a la derecha); confirmar que en zoom 100% el arrastre con click derecho no tiene ningún efecto visible (clampeado).

7. **`controller/ocr_controller.py`: recorte con click izquierdo siempre activo, y botón simplificado.** Quitar la condición `self._crop_mode_active or self._crop_box is not None` del `eventFilter` para el botón izquierdo: el arrastre con click izquierdo sobre `preview_label` queda siempre habilitado (independientemente de si ya existe `_crop_box`). Simplificar `on_crop_toggled()` (conectado a la señal `crop_toggled`, que ahora solo se dispara si el botón está habilitado, es decir si hay recorte) para que únicamente limpie `self._crop_box`, oculte el rectángulo y llame `view.update_crop_button(has_crop=False)`. En `_on_crop_mouse_release()`, cuando se confirma un recorte válido, llamar `view.update_crop_button(has_crop=True)` (sin el parámetro `armed`); cuando se descarta por umbral mínimo sin recorte previo, no queda ningún estado de "armado" que cancelar (ya no existe). Ajustar `on_open_image()` para llamar `view.update_crop_button(has_crop=False)` sin `armed`.
   Prueba manual: cargar una imagen, arrastrar directamente con click izquierdo sobre un fragmento de texto sin tocar ningún botón, confirmar que queda el recorte dibujado y `crop_button` pasa a habilitado ("Quitar recorte"); arrastrar de nuevo para redefinir; clickear "Quitar recorte" y confirmar que el botón vuelve a deshabilitarse y "Transcribir" vuelve a procesar la imagen completa.

8. **`controller/ocr_controller.py`: botón "Restablecer zoom".** Conectar `reset_zoom_button.clicked` a un nuevo método `on_reset_zoom()` que setea `self._zoom = 1.0`, `self._zoom_center` al centro de `self._preview_source`, y llama `_render_preview()`.
   Prueba manual: aplicar zoom y paneo, clickear "Restablecer zoom", confirmar que la vista vuelve exactamente al estado inicial (imagen completa ajustada, `zoom_label` oculto).

9. **Verificación end-to-end.** Recorrido manual completo: abrir imagen grande y otra chica; hacer zoom con la rueda centrado en distintos puntos; panear con click derecho en varias direcciones; dibujar un recorte con zoom aplicado y confirmar que el fragmento transcripto corresponde exactamente a lo que se ve resaltado (no a coordenadas desalineadas); quitar el recorte; restablecer zoom; redimensionar la ventana con zoom/paneo activo y confirmar que la imagen y el recorte (si existe) se reposicionan correctamente; cargar una imagen nueva y confirmar que resetea zoom/paneo/recorte; alternar tema; confirmar que "OCR en vivo" (specs 08-09, 11) sigue funcionando sin regresiones. Revisión de imports rotos.
   Prueba: recorrido manual + revisión de imports rotos.

## Acceptance criteria

- [x] Girar la rueda del mouse sobre la vista previa aumenta/disminuye el zoom en pasos de `ZOOM_STEP` (25%), clampeado entre 100% y 500%.
- [x] El zoom se centra en el punto de la imagen bajo el cursor: ese punto permanece fijo en pantalla antes y después de cada paso de zoom.
- [x] Arrastrar con click derecho sobre la vista previa desplaza (panea) la imagen visible cuando el zoom es mayor a 100%; el contenido se mueve de forma natural en la dirección del arrastre.
- [x] En zoom 100%, el arrastre con click derecho no tiene ningún efecto (la imagen completa ya está a la vista, sin nada para desplazar).
- [x] El paneo nunca deja ver áreas fuera de los límites de la imagen original (clampeado en ambos ejes).
- [x] Aparece un indicador flotante de porcentaje de zoom (ej. "150%") en la esquina inferior derecha de la vista previa, visible solo cuando el zoom es distinto de 100%.
- [x] El botón "Restablecer zoom" vuelve la vista previa a 100% (imagen completa ajustada) y oculta el indicador de zoom, sin importar cuánto zoom/paneo se haya aplicado antes.
- [x] Arrastrar con click izquierdo sobre la vista previa selecciona/redefine el área de recorte directamente, sin necesidad de clickear ningún botón antes (a diferencia de spec 10).
- [x] Con un recorte ya dibujado, arrastrar de nuevo con click izquierdo lo redefine (se mantiene el comportamiento de spec 10).
- [x] El botón de recorte (`crop_button`) está deshabilitado y muestra "Quitar recorte" mientras no hay región seleccionada; se habilita al confirmarse un recorte válido; clickearlo limpia el recorte y vuelve a deshabilitarse.
- [x] Con zoom y/o paneo aplicados, dibujar un recorte sobre un fragmento de texto específico y transcribirlo produce el texto correspondiente exactamente a ese fragmento (no a coordenadas desalineadas por el zoom).
- [x] Un recorte ya confirmado se reposiciona correctamente sobre la vista previa al hacer zoom, panear, o redimensionar la ventana, sin quedar desalineado.
- [x] Cargar una imagen nueva con "Abrir imagen" resetea zoom a 100%, paneo al centro, y limpia cualquier recorte activo.
- [x] Quitar el recorte ("Quitar recorte") **no** resetea el zoom ni el paneo actual.
- [x] El flujo de "OCR de imágenes" para imágenes que requieren tiling (spec 02) y preprocesamiento multi-variante (spec 03) sigue funcionando sin regresiones, con o sin zoom/paneo aplicado.
- [x] El flujo de "OCR en vivo" (specs 08-09, 11) sigue funcionando sin regresiones (no se tocó `LiveOcrView` ni `ScreenOverlay`).
- [x] MVC respetado: `view/ocr_view.py` no contiene lógica de cálculo de zoom/paneo/mapeo de coordenadas; toda esa lógica vive en `OcrController`; `model/` no se modifica.
- [x] No hay menú contextual nativo al hacer click derecho sobre la vista previa.
- [x] Los controles y el indicador de zoom son legibles y consistentes en ambos temas (claro/oscuro).

## Decisions

- **Sí:** el recuadro donde se dibuja la imagen dentro de `preview_label` (offset y tamaño del letterbox) permanece fijo sin importar el zoom; lo único que cambia es qué región de la imagen original se recorta y estira para llenar ese recuadro. Evita reimplementar el letterboxing dinámicamente en cada nivel de zoom y mantiene sin cambios toda la lógica de `_crop_box` (sigue en coordenadas de imagen original, independiente de zoom/paneo).
- **Sí:** el zoom es relativo a "ajustado a ventana" (1.0 = fit actual) en vez de un porcentaje absoluto sobre la resolución original. Consistente con que la vista previa siempre reescala según el tamaño de `preview_label` (ya lo hacía antes de esta spec); un zoom absoluto sería confuso al redimensionar la ventana.
- **Sí:** zoom centrado en el cursor (el punto de la imagen bajo el mouse permanece fijo al hacer scroll), en vez de centrado en el medio de la preview. Permite acercar un fragmento específico de texto sin tener que panear después para recentrarlo — flujo más natural para el caso de uso de recortar texto específico.
- **Sí:** rango de zoom fijo 100%–500% con paso de 25% por notch de rueda, sin configuración de usuario. Rango suficiente para acercar texto pequeño en imágenes de alta resolución sin sobre-ingeniería (límites configurables no pedidos).
- **Sí:** el paneo con click derecho se clampea para no permitir mover la imagen fuera de sus límites, y no tiene efecto en zoom 100%. Evita un estado visualmente confuso (áreas vacías dentro de la preview) y es consistente con que en 100% no hay nada fuera de vista para revelar.
- **Sí:** click izquierdo selecciona/redefine el recorte siempre, sin botón de armado previo (cambio respecto a spec 10). El pedido explícito del usuario reemplaza la decisión original de spec 10 de requerir "Activar recorte"; el botón se simplifica a una única acción ("Quitar recorte"), reduciendo un paso de fricción para el flujo principal.
- **Sí:** `crop_button` deshabilitado (en vez de oculto) cuando no hay recorte activo. Consistente con el patrón ya usado en el proyecto para `transcribe_button` (deshabilitado sin imagen cargada) en vez de ocultar/mostrar controles dinámicamente.
- **Sí:** indicador de zoom como `QLabel` flotante superpuesto en la esquina inferior derecha de `preview_label`, visible solo cuando el zoom es distinto de 100%, en vez de vivir en la toolbar. Mantiene la toolbar sin controles adicionales y da feedback visual directamente sobre lo que se está viendo, ocultándose cuando no aporta información (100% es el estado esperado por defecto).
- **Sí:** quitar el recorte no resetea zoom/paneo, pero cargar una imagen nueva sí resetea ambos junto con el recorte. El caso de uso típico es ajustar el recorte varias veces mientras se mantiene el mismo nivel de zoom para precisión; cargar una imagen nueva no tiene relación con el estado visual anterior.
- **Sí:** sin atajos de teclado (+/-) ni doble-click para resetear zoom; único mecanismo de reset es el botón dedicado "Restablecer zoom". Evita ambigüedad con el doble-click (que podría confundirse con parte del gesto de arrastre de recorte) y mantiene el control explícito y descubrible.
- **No:** extender zoom/paneo a `LiveOcrView`/`ScreenOverlay`. El overlay de spec 08 ya cumple el rol de selección de región para OCR en vivo; agregar zoom ahí es un caso de uso distinto no pedido en esta spec.
- **No:** permitir mover/redimensionar el rectángulo de recorte con handles (se mantiene la decisión de spec 10). Fuera de alcance de esta spec, que se enfoca en zoom/paneo y en simplificar la activación del recorte.
- **Sí:** por defecto, las pruebas manuales de cada paso del plan de implementación las ejecuta el usuario, no el asistente; el asistente solo verifica por otros medios (lectura de código, `grep`, chequeo de imports) cuando el usuario no pueda evaluar el cambio corriendo el proyecto. Mismo default heredado de specs 09, 10 y 11.

## Risks

| Risk | Mitigation |
|---|---|
| El mapeo de coordenadas entre la vista previa y la imagen original ahora depende de la región visible (zoom + paneo), no solo del letterbox fijo de spec 10. Un error en `_current_visible_region()` o en las fórmulas de `_map_point_to_original()`/`_redraw_crop_rect()` desalinearía el recorte respecto a lo que el usuario ve, silenciosamente. | El paso 4 reutiliza el mismo patrón de mapeo ya validado en spec 10 (escala + offset), parametrizado sobre la región visible en vez de la imagen completa; el paso 9 exige verificar explícitamente con zoom aplicado que el texto transcripto corresponde exacto al fragmento resaltado. |
| Zoom centrado en el cursor requiere recalcular `_zoom_center` en cada notch de rueda a partir del punto de imagen bajo el cursor; un error de signo o de orden de operaciones (mapear antes vs. después de cambiar `_zoom`) haría que el punto "salte" en vez de quedar fijo. | El paso 5 especifica explícitamente mapear el punto usando la región visible **antes** de aplicar el nuevo zoom, y verificar visualmente que el fragmento bajo el cursor no se desplaza al hacer zoom in/out repetido. |
| Al quitar la condición de "armado" del recorte (paso 7), un arrastre accidental con click izquierdo sobre la vista previa (ej. al intentar hacer otra cosa) podría generar un recorte no deseado con más frecuencia que antes, ya que no hace falta ningún paso previo. | Se mantiene el umbral mínimo (`CROP_MIN_SIZE`) de spec 10 para descartar clicks/arrastres accidentales pequeños; fue un pedido explícito del usuario priorizar la rapidez del flujo sobre la fricción de un botón de armado. |
| Paneo con click derecho y zoom con rueda ocurren sobre el mismo widget que ya maneja el arrastre de recorte con click izquierdo; una implementación descuidada del `eventFilter` podría mezclar el estado de un gesto con otro (ej. iniciar un paneo mientras hay un arrastre de recorte en curso). | El paso 6 distingue los gestos por botón del mouse (`event.button()`) y por variables de estado independientes (`_pan_drag_start` vs. `_crop_drag_start`), evitando que un gesto interfiera con el otro; se verifica en el paso 9 alternando gestos en la misma sesión. |
| Reescalar un recorte de la imagen original a un tamaño de destino fijo en cada frame de zoom/paneo (potencialmente en cada evento de rueda o move del mouse) puede introducir lag perceptible en imágenes de muy alta resolución. | No se agrega debounce adicional a los eventos de zoom/paneo en esta spec (se acepta el costo de recalcular en cada evento, igual que ya se hace hoy con el resize de la preview vía `PREVIEW_RESIZE_DEBOUNCE_MS`); si en la verificación del paso 9 se detecta lag notorio, queda como ajuste de rendimiento a evaluar por separado, fuera de alcance de esta spec. |
