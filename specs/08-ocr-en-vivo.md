# SPEC 08 — OCR en vivo (captura de segmento de pantalla)

> **Status:** Aprobado
> **Depends on:** `specs/07-menu-configuracion-sidebar.md`
> **Date:** 2026-07-13
> **Objective:** Habilitar la opción "OCR en vivo" del sidebar para transcribir de forma asíncrona y continua un segmento de pantalla que el usuario posiciona y redimensiona con un overlay flotante, reutilizando el motor Tesseract y el preprocesamiento multi-variante ya existentes.

## Scope

**In:**

- **`view/sidebar_view.py`**: se habilita el botón "OCR en vivo" (hoy deshabilitado, placeholder desde spec 05), pasa a formar parte de la exclusividad mutua con "OCR de imágenes" y "Configuración". Emite una nueva señal `live_ocr_selected`.
- **Nuevo `view/live_ocr_view.py`** (`LiveOcrView(QWidget)`): vista de contenido análoga a `OcrView` pero sin el módulo "Abrir imagen". Layout de dos columnas: izquierda con un `QLabel` de miniatura mostrando la última captura del segmento (mismo patrón que `preview_label`), derecha con el `QTextEdit` de resultado (solo lectura, se actualiza sola). Arriba, un `QComboBox` de idioma (mismas 3 opciones: Español/Inglés/Ambos) y un botón **"Activar selección"** que crea el overlay y arranca el polling; se deshabilita mientras el overlay ya está abierto y se re-habilita cuando el usuario lo cierra con la X.
- **Nuevo `view/screen_overlay.py`** (`ScreenOverlay(QWidget)`): ventana top-level frameless, siempre-encima, semitransparente, con borde de acento y handles en las esquinas para redimensionar, y un botón/X pequeño en una esquina para cerrarla. Aparece centrada con tamaño default al activarse. Se puede arrastrar (mover) desde el área central y redimensionar desde los handles, en cualquier monitor conectado. Expone señales de posición/tamaño para que el controller dispare capturas, y una señal `closed` cuando el usuario clickea la X.
- **Nuevo `model/image_diff.py`**: función que compara dos imágenes (usando `numpy`, ya aprobado) y determina si hubo un cambio significativo, para evitar retranscribir cuando el contenido de pantalla es idéntico al último poll.
- **`model/ocr_model.py` ampliado**: se expone una función pública que recibe una `PIL.Image` en memoria (no una ruta de archivo) y aplica el mismo preprocesamiento multi-variante + selección por confianza que ya usa `transcribe_large_image` internamente (`_transcribe_best_variant`), sin tiling (el segmento en vivo ya es del tamaño que el usuario definió).
- **Nuevo `controller/live_ocr_controller.py`** (`LiveOcrController`): orquesta el ciclo completo — crea/destruye el `ScreenOverlay`, corre un `QTimer` de polling que oculta el overlay, captura la pantalla con `QScreen.grabWindow` en el área del overlay, la vuelve a mostrar, compara contra la captura anterior vía `model/image_diff.py`, y si cambió dispara una transcripción asíncrona (mismo patrón `QThread` que `TranscriptionWorker` en `ocr_controller.py`) usando la nueva función de `ocr_model.py`. Actualiza la miniatura y el texto de `LiveOcrView` en cada captura/resultado.
- **`model/config_model.py`**: se agrega lectura de una clave `"engine"` en `config.json` (default `"tesseract"` si no existe la clave) para uso futuro; `LiveOcrController` la lee al iniciar una transcripción, aunque hoy solo exista la rama Tesseract (el combobox de Configuración sigue siendo placeholder deshabilitado, sin escritor, según spec 07).
- **`view/main_window.py`**: agrega `LiveOcrView` al `content_stack`, conecta `sidebar_view.live_ocr_selected`, instancia `LiveOcrController`. Al navegar fuera de "OCR en vivo" (a "OCR de imágenes" o "Configuración"), se detiene el polling y se cierra el overlay si estaba abierto.
- **`view/metro_style.py`**: estilos para el borde/handles del `ScreenOverlay` (acento azul, semitransparente) y para los nuevos widgets de `LiveOcrView` (botón "Activar selección", miniatura), en ambos temas claro/oscuro.

**Out (para futuras specs):**

- Implementar un motor OCR distinto a Tesseract (Claude Haiku u otro); la clave `"engine"` se lee pero no hay lógica de selección real todavía.
- Guardado del texto transcrito a archivo o historial entre sesiones (ya fuera de alcance del MVP original).
- Recordar la última posición/tamaño del overlay entre activaciones o entre sesiones (cada activación arranca en la posición/tamaño default).
- Configurar el intervalo de polling o el umbral de detección de cambios desde la UI (quedan como constantes internas).
- Captura de audio o video, solo imagen estática por poll.

## Data model

```python
# model/config_model.py (ampliación)

def load_config() -> dict:
    """... (sin cambios de firma)
    Agrega config.setdefault("engine", "tesseract") junto al setdefault de "theme"
    existente, para que cualquier lector de la config tenga la clave garantizada.
    """
```

```python
# model/image_diff.py (nuevo)

def has_changed(previous: Image.Image | None, current: Image.Image, threshold: float = ...) -> bool:
    """Compara `previous` (última captura, o None si es la primera) contra `current`
    usando numpy (diferencia absoluta media de píxeles tras normalizar tamaño/modo).
    Devuelve True si el cambio supera `threshold` o si `previous` es None (primera
    captura siempre dispara transcripción). Sin dependencias de PySide6/pytesseract."""
```

```python
# model/ocr_model.py (ampliación)

def transcribe_image_variants(image: Image.Image, language_code: str, tesseract_path: str | None) -> str:
    """Transcribe una PIL.Image ya en memoria (sin ruta de archivo ni tiling), aplicando
    generate_variants + selección por confianza — misma lógica que ya usa internamente
    transcribe_large_image (_transcribe_best_variant), reutilizada aquí como función
    pública para el flujo de captura de pantalla en vivo."""
```

```python
# view/screen_overlay.py (nuevo)

class ScreenOverlay(QWidget):
    """Ventana top-level frameless, siempre-encima, semitransparente, con borde de
    acento y handles de redimensión en las esquinas. Arrastrable desde el área central.
    No contiene lógica de negocio ni de captura: solo geometría/dibujo y señales."""

    closed = Signal()          # al clickear la X
    geometry_changed = Signal()  # al terminar de mover o redimensionar (mouseReleaseEvent)

    def capture_geometry(self) -> QRect:
        """Devuelve el QRect (coordenadas globales de pantalla) del área interior
        a capturar, excluyendo el borde/handles dibujados por el propio overlay."""
```

```python
# view/live_ocr_view.py (nuevo)

class LiveOcrView(QWidget):
    """Vista de contenido de OCR en vivo: selector de idioma, botón 'Activar selección',
    miniatura de la última captura y resultado de texto (solo lectura, se actualiza sola).
    No contiene lógica de negocio ni de captura de pantalla."""

    activate_selection_clicked = Signal()

    def set_preview_image(self, pixmap: QPixmap) -> None: ...
    def set_result_text(self, text: str) -> None: ...
    def get_selected_language(self) -> str: ...
    def enable_activate_button(self) -> None: ...
    def disable_activate_button(self) -> None: ...
```

```python
# controller/live_ocr_controller.py (nuevo)

class LiveOcrController(QObject):
    """Orquesta el ciclo completo de OCR en vivo: crea/destruye ScreenOverlay, corre el
    QTimer de polling (oculta overlay → QScreen.grabWindow → muestra overlay → diff vía
    model/image_diff.py → si cambió, dispara transcripción async con QThread, igual
    patrón que TranscriptionWorker), y actualiza LiveOcrView con cada captura/resultado.
    Expone start()/stop() para que MainWindow los invoque al navegar entre vistas."""
```

`config.json` gana la clave `"engine"` (default `"tesseract"`, sin escritor todavía — se lee pero no se persiste desde ningún flujo nuevo).

## Implementation plan

1. **`model/config_model.py`: agregar default de `"engine"`.** En `load_config()`, agregar `config.setdefault("engine", "tesseract")` junto al `setdefault("theme", "dark")` existente.
   Prueba manual: `python -c "from model.config_model import load_config; print(load_config())"`, confirmar que aparece `"engine": "tesseract"` aunque `config.json` no tenga esa clave.

2. **Nuevo `model/image_diff.py`: `has_changed()`.** Implementar comparación de dos `PIL.Image` vía `numpy` (normalizar tamaño/modo si difieren, calcular diferencia absoluta media de píxeles, comparar contra un umbral constante definido en el módulo). `previous=None` siempre devuelve `True`.
   Prueba manual: `python -c "from PIL import Image; from model.image_diff import has_changed; a=Image.new('RGB',(50,50),'white'); b=a.copy(); print(has_changed(a,b))"` → `False`; repetir pintando un pixel distinto en `b` → `True`.

3. **`model/ocr_model.py`: exponer `transcribe_image_variants()`.** Renombrar/generalizar `_transcribe_best_variant` a una función pública que reciba una `PIL.Image` ya en memoria, aplique `tesseract_cmd` si corresponde, y devuelva el texto de la variante con mejor confianza (misma lógica ya usada por `transcribe_large_image`, sin tiling).
   Prueba manual: `python -c "from PIL import Image; from model.ocr_model import transcribe_image_variants; print(transcribe_image_variants(Image.open('alguna_imagen.png'), 'spa+eng', None))"` devuelve texto sin error; confirmar que `transcribe_large_image` sigue funcionando igual (no se rompió el llamado interno).

4. **Nuevo `view/screen_overlay.py`: `ScreenOverlay`.** Ventana `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool`, fondo semitransparente, borde de acento dibujado en `paintEvent`, handles en las 4 esquinas (áreas de `mousePressEvent`/`mouseMoveEvent` para redimensionar) y botón "✕" pequeño en una esquina (cierra y emite `closed`). Arrastre desde el área central (fuera de handles) mueve la ventana. `geometry_changed` se emite en `mouseReleaseEvent` tras mover o redimensionar. `capture_geometry()` devuelve el `QRect` interior sin el borde.
   Prueba manual: instanciar `ScreenOverlay` sola desde un script de prueba, confirmar que aparece centrada, se puede arrastrar, redimensionar desde las esquinas, y que la X la cierra emitiendo la señal (imprimir en un slot de prueba).

5. **Nuevo `view/live_ocr_view.py`: `LiveOcrView`.** Layout de dos columnas igual a `OcrView` sin "Abrir imagen": arriba `QComboBox` de idioma + botón "Activar selección" (`activate_selection_clicked`); izquierda `QLabel` de miniatura (`objectName="previewLabel"`, mismo patrón que `OcrView`); derecha `QTextEdit` de solo lectura. Métodos `set_preview_image`, `set_result_text`, `get_selected_language`, `enable_activate_button`, `disable_activate_button`.
   Prueba manual: instanciar `LiveOcrView` sola, confirmar que el layout se ve análogo a `OcrView` pero sin botón de abrir imagen, y que los setters no explotan al llamarlos con datos de prueba.

6. **`view/metro_style.py`: estilos de `ScreenOverlay` y `LiveOcrView`.** Agregar reglas para el borde/handles del overlay (acento `rgb(42,130,218)`, fondo semitransparente) y para el botón "Activar selección" (mismo estilo que otros `QPushButton` ya definidos), espejando dark/light.
   Prueba manual: alternar tema en Configuración y confirmar visualmente que `LiveOcrView` y el overlay se ven consistentes en ambos temas (sin texto/bordes ilegibles).

7. **`view/sidebar_view.py`: habilitar "OCR en vivo".** Quitar `setEnabled(False)` del botón existente, hacerlo checkable, integrarlo a la lógica de exclusividad mutua ya generalizada en spec 07 (ahora entre `ocr_button`, `live_ocr_button`, `settings_button`). Emitir `live_ocr_selected` al clickear.
   Prueba manual: instanciar `SidebarView` sola, confirmar que "OCR en vivo" ya no aparece deshabilitado, y que clickear cualquiera de los tres botones resalta solo ese y destilda los otros dos.

8. **Nuevo `controller/live_ocr_controller.py`: `LiveOcrController`.** Implementa `start()` (crea `ScreenOverlay`, lo posiciona/dimensiona con tamaño default centrado, conecta `closed`/`geometry_changed`, arranca `QTimer` de polling) y `stop()` (detiene timer, cierra y destruye overlay si existe). En cada tick del timer: oculta overlay → `QGuiApplication.primaryScreen().grabWindow(0, *capture_geometry)` (o la screen correspondiente al monitor actual) → muestra overlay → convierte `QPixmap` a `PIL.Image` → `image_diff.has_changed()` contra la captura previa → si cambió, lanza un `QThread` worker (mismo patrón que `TranscriptionWorker`) que llama a `transcribe_image_variants()` con `resolve_tesseract_path()` y actualiza `LiveOcrView` (miniatura siempre se actualiza; texto solo si cambió y la transcripción tuvo éxito). Al recibir `closed` del overlay, deja el botón "Activar selección" habilitado de nuevo sin tocar el resto del estado. Conecta `LiveOcrView.activate_selection_clicked` a `start()` (no-op si ya hay un overlay activo).
   Prueba manual: activar OCR en vivo sobre un bloque de texto en pantalla, confirmar que la miniatura y el texto se actualizan solos sin tocar ningún botón de "transcribir"; mover el overlay sobre otro texto y confirmar que se retranscribe; dejarlo quieto sobre contenido estático y confirmar que no se re-dispara Tesseract en cada poll (agregar un `print` temporal para verificar, quitarlo antes de cerrar el paso); cerrar con la X y confirmar que el botón "Activar selección" vuelve a habilitarse.

9. **`view/main_window.py`: integración final.** Agregar `LiveOcrView` al `content_stack`, conectar `sidebar_view.live_ocr_selected` para navegar a esa vista, instanciar `LiveOcrController(live_ocr_view)`. Conectar la navegación a **cualquier otra** vista (OCR de imágenes, Configuración) para llamar `live_ocr_controller.stop()` si estaba corriendo.
   Prueba manual: `python main.py`, activar OCR en vivo, confirmar overlay + polling funcionando; navegar a "OCR de imágenes" y confirmar que el overlay se cierra solo y el polling se detiene; volver a "OCR en vivo" y confirmar que hay que clickear "Activar selección" de nuevo (no recuerda posición anterior).

10. **Verificación end-to-end.** Repetir el flujo completo: activar selección, mover/redimensionar el overlay sobre distinto texto en pantalla, confirmar transcripción asíncrona sin botones, cerrar con X, reactivar, navegar entre las tres secciones del sidebar sin que quede el overlay o el timer huérfano, y confirmar que el flujo de "OCR de imágenes" (spec 01-03) sigue funcionando sin regresiones. Confirmar `grep -r "OCR en vivo"` no deja referencias a "próximamente"/deshabilitado fuera de este archivo de spec y specs históricas.
    Prueba: recorrido manual completo + revisión de imports rotos.

## Acceptance criteria

- [ ] El sidebar muestra "OCR en vivo" habilitado (ya no como placeholder deshabilitado), integrado a la exclusividad mutua con "OCR de imágenes" y "Configuración".
- [ ] Al entrar a "OCR en vivo" y clickear "Activar selección", aparece un overlay centrado, semitransparente, con borde de acento y handles en las esquinas, siempre-encima del resto de ventanas.
- [ ] El overlay se puede mover arrastrándolo desde el área central y redimensionar desde los handles de las esquinas, en cualquier monitor conectado.
- [ ] Sin clickear ningún botón de "transcribir", el texto de `LiveOcrView` se actualiza solo cuando el contenido de pantalla dentro del overlay cambia (por movimiento/redimensión del overlay o por cambio del contenido subyacente).
- [ ] Si el contenido capturado es idéntico al del poll anterior, no se dispara una nueva transcripción (el texto ya mostrado permanece igual).
- [ ] La miniatura de `LiveOcrView` refleja la última captura realizada.
- [ ] El overlay no se auto-captura (su propio borde/botón X no aparece como ruido en el texto transcrito).
- [ ] Clickear la X del overlay lo cierra y detiene el polling, pero la vista "OCR en vivo" sigue activa en el content area con el botón "Activar selección" nuevamente habilitado.
- [ ] Clickear "Activar selección" con el overlay ya cerrado lo vuelve a crear en la posición/tamaño default.
- [ ] Navegar del sidebar a "OCR de imágenes" o "Configuración" mientras OCR en vivo está activo cierra el overlay y detiene el polling automáticamente.
- [ ] El selector de idioma (Español/Inglés/Ambos) de `LiveOcrView` afecta la transcripción en vivo igual que en OCR de imágenes.
- [ ] Si Tesseract no está configurado (ni en PATH ni en `config.json`), activar OCR en vivo dispara el mismo flujo de selección manual de ruta que ya existe en OCR de imágenes.
- [ ] El flujo completo de "OCR de imágenes" (spec 01-03) sigue funcionando sin regresiones tras los cambios.
- [ ] `config.json` gana la clave `"engine"` (default `"tesseract"`) sin perder ni sobreescribir `tesseract_path`/`theme` existentes.
- [ ] MVC respetado: `ScreenOverlay`/`LiveOcrView` no llaman a `pytesseract` ni a `QScreen.grabWindow` con lógica de negocio embebida (la orquestación vive en `LiveOcrController`); `model/image_diff.py` y `model/ocr_model.py` no importan PySide6.
- [ ] No hay texto ilegible (bajo contraste) en `LiveOcrView` ni en el overlay bajo ningún tema (claro/oscuro).

## Decisions

- **Sí:** overlay flotante arrastrable/redimensionable en vez de dibujar el rectángulo una sola vez. Permite ajustar la selección sobre la marcha sin reactivar el flujo, que es el caso de uso natural de "OCR en vivo" (seguir texto que se mueve o cambia de posición en pantalla).
- **Sí:** captura vía `QScreen.grabWindow` (PySide6, ya aprobado) en vez de una librería externa nueva (`mss`/`pyautogui`). Cumple la restricción del proyecto de evitar dependencias adicionales; el usuario aceptó que una librería dedicada quede como posible spec futura si `grabWindow` resulta insuficiente en la práctica.
- **Sí:** polling periódico con diff de píxeles (`numpy`) en vez de solo debounce por movimiento del overlay. Cubre tanto el caso de mover/redimensionar el recuadro como el de contenido dinámico en pantalla que cambia sin que el usuario toque el overlay (ej. un contador, texto que se actualiza solo), evitando además retranscribir cuando no hubo cambios.
- **Sí:** ocultar el overlay brevemente antes de cada captura y volver a mostrarlo, en vez de aceptar que su borde se cuele en el OCR. Es el patrón estándar de herramientas de recorte de pantalla; con un intervalo de polling de un par de segundos el parpadeo es imperceptible.
- **Sí:** reutilizar `generate_variants` + selección por confianza (mismo mecanismo que OCR de imágenes) para cada captura en vivo, en vez de transcripción simple. El usuario priorizó calidad de reconocimiento sobre velocidad máxima de polling.
- **Sí:** si no hay cambios respecto al poll anterior, se deja el texto ya mostrado tal cual (sin limpiarlo ni mostrar un estado "sin cambios"). Evita parpadeo visual innecesario en el resultado cuando el contenido de pantalla es estable.
- **Sí:** la X del overlay solo cierra el overlay y detiene el polling, sin desactivar la vista "OCR en vivo" del sidebar ni navegar a otra sección. Se agrega un botón explícito "Activar selección" en `LiveOcrView` para reabrirlo, dejando el control de reactivación dentro del content area en vez de comportamiento implícito.
- **Sí:** el overlay no recuerda posición/tamaño entre activaciones ni entre sesiones (arranca siempre centrado con tamaño default). Simplifica el alcance; queda para una spec futura si se pide persistencia de la última selección.
- **Sí:** soporte multi-monitor sin lógica especial más allá de usar las coordenadas globales del overlay (ventana top-level estándar de Qt). No se agrega detección explícita de "a qué monitor pertenece" más allá de lo que Qt resuelve automáticamente vía coordenadas globales.
- **Sí:** navegar a otra sección del sidebar detiene el polling y cierra el overlay automáticamente (no persiste en segundo plano). Evita procesos huérfanos consumiendo CPU/Tesseract cuando el usuario ya no está mirando el resultado.
- **Sí:** se agrega la clave `"engine"` a `config.json` (default `"tesseract"`, leída pero sin escritor todavía) aunque hoy solo exista un motor real. Deja el terreno preparado para cuando el combobox de Configuración (spec 07) deje de ser placeholder, sin necesidad de otra migración de esquema de `config.json` en ese momento.
- **No:** implementar selección real de motor OCR (Tesseract vs. Claude Haiku) en esta spec. La clave `"engine"` se lee pero la única rama funcional sigue siendo Tesseract; el combobox de Configuración sigue deshabilitado según lo decidido en spec 07.
- **No:** persistir el texto transcrito en vivo a archivo o historial. Fuera de alcance del MVP original y no mencionado como necesidad para OCR en vivo.
- **No:** exponer configuración de intervalo de polling o umbral de diff desde la UI. Quedan como constantes internas ajustables en código; no hay pedido explícito de hacerlas configurables por el usuario.

## Risks

| Risk | Mitigation |
|---|---|
| El polling con Tesseract corriendo cada pocos segundos puede consumir CPU de forma notable, sobre todo con `generate_variants` ejecutando varias pasadas por captura. | El paso 8 del plan corre la transcripción en un `QThread` separado (no bloquea la UI); el diff de píxeles (paso 2) evita retranscribir cuando no hay cambios reales, limitando las pasadas de Tesseract a los casos donde realmente hace falta. |
| Ocultar/mostrar el overlay en cada poll (para evitar auto-captura) puede generar parpadeo visible o timing incorrecto si `grabWindow` se dispara antes de que Qt termine de ocultar la ventana. | El paso 4 prueba el overlay aislado; el paso 8 exige verificar manualmente que no aparezca el borde/X del overlay como ruido en el texto transcrito, ajustando el orden ocultar→esperar repaint→capturar→mostrar si hace falta. |
| Si el usuario redimensiona el overlay a un tamaño muy chico (ej. unos pocos píxeles), `QScreen.grabWindow` o `generate_variants` podrían fallar o devolver resultados sin sentido. | El paso 4 puede agregar un tamaño mínimo al redimensionar (ej. 40x40px) para evitar el caso degenerado, documentado como ajuste dentro del mismo paso si aparece durante la implementación. |
| Un worker de transcripción lanzado en un poll puede seguir corriendo cuando ya llegó un nuevo poll con contenido distinto (overlap), generando resultados desactualizados que pisen a uno más reciente. | El paso 8 debe ignorar resultados de un worker si ya se lanzó uno más nuevo (guardar una referencia al worker "vigente" y descartar señales de workers viejos), siguiendo un patrón similar al ya usado para descartar transcripciones obsoletas. |
| Detener el polling al navegar fuera de "OCR en vivo" (paso 9) podría dejar un `QThread` de transcripción todavía corriendo en segundo plano si la navegación ocurre a mitad de una transcripción. | El paso 9 debe confirmar que `stop()` no intenta destruir el overlay mientras un worker sigue vivo sin antes desconectar sus señales, evitando updates a una `LiveOcrView` que ya no está activa; se prueba navegando fuera justo durante una transcripción en curso. |
| Multi-monitor con distinto DPI/escalado podría hacer que las coordenadas del overlay no coincidan exactamente con el área capturada por `grabWindow`. | Se documenta como riesgo conocido de Qt con escalado de pantalla no estándar; si aparece durante la verificación del paso 10, se ajusta el mapeo de coordenadas dentro del mismo paso en vez de bloquear el resto de la spec. |
