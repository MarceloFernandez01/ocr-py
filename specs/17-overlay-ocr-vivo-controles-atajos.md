# Spec 17 — Overlay de OCR en vivo: captura limpia, controles legibles y atajos globales

**Estado:** aprobado
**Dependencias:** `specs/08-ocr-en-vivo.md` (overlay y ciclo de polling), `specs/09-live-ocr-boton-iniciar-transcripcion.md` (separación entre activar selección e iniciar transcripción), `specs/11-traduccion-ocr-en-vivo.md` (toggle de traducción), `specs/16-filtro-cambio-texto-ocr-vivo.md` (patrón de controles nuevos en Configuración persistidos en `config.json`)
**Fecha:** 2026-08-20
**Objetivo:** Sacar los handles de redimensión del área capturada y volver manejable el overlay de OCR en vivo con botones más grandes, indicador de estado, botón de traducción y atajos de teclado globales configurables.

## Contexto

`ScreenOverlay` pinta cuatro cuadrados de acento de `HANDLE_SIZE = 16` px en las esquinas del área de selección, pero `capture_geometry()` solo descuenta `BORDER_WIDTH = 4` px. Los 12 px restantes de cada cuadrado entran en la imagen que se manda al OCR: ensucian la transcripción y, peor, son píxeles que `has_changed` puede leer como cambio. Ocultarlos en cada captura y volver a mostrarlos produciría un parpadeo constante, así que la salida es que dejen de existir como dibujo.

En paralelo, la barra de control tiene dos botones de 20×20 px con un solo carácter (`✕`, `▶`), sin rótulo ni tooltip: hay que adivinar qué hacen y son difíciles de acertar con el mouse. Tampoco hay forma de saber, mirando el overlay, si la transcripción está corriendo, ni de pausarla sin volver a la ventana de la aplicación — que es justamente lo que el flujo de OCR en vivo evita, porque el usuario está trabajando en otra ventana.

## Alcance

**Dentro del alcance:**

- `view/screen_overlay.py`: dejar de pintar los cuatro handles de esquina. La zona de agarre de 16 px se conserva intacta y se señaliza con el cursor (`Qt.SizeFDiagCursor` / `Qt.SizeBDiagCursor`) al pasar el mouse por encima.
- Botones de la barra de control a 32×32 px, con tooltip que nombra la acción e incluye el atajo vigente.
- Botón de traducción nuevo en la barra de control, espejo del `translation_button` que ya existe en `LiveOcrView`: ambos comparten estado y cualquiera de los dos lo alterna. Deshabilitado mientras la transcripción no esté corriendo.
- Indicador de estado con cuatro estados (Detenido, Transcribiendo, Analizando…, Pausado) en la barra de control del overlay, replicado en `LiveOcrView`.
- Atajos de teclado **globales** de Windows para pausar/reanudar y cerrar el overlay, activos mientras la aplicación esté abierta. Con el overlay cerrado, el atajo de pausar/reanudar activa la selección y arranca la transcripción.
- Atajos configurables desde Configuración con `QKeySequenceEdit`, persistidos en `config.json`, con validación de modificador obligatorio y aviso si Windows rechaza el registro.
- Dos módulos nuevos: `model/hotkey_model.py` (traducción y validación de la combinación, sin PySide6) y `controller/global_hotkeys.py` (registro nativo vía `ctypes` y filtro de eventos de Qt).
- Actualizar `CLAUDE.md`.

**Fuera del alcance (para specs futuras):**

- Mostrar el texto reconocido o la traducción dentro o al lado del overlay: el overlay sigue siendo solo selección y control.
- Atajos globales en macOS y Linux. `RegisterHotKey` es API de Windows; en otro sistema los atajos quedan inactivos y la aplicación funciona igual con sus botones.
- Atajos para activar la traducción, cambiar de idioma o mover la región.
- Recortar o enmascarar los cuadrados en la imagen antes del OCR (opción descartada: ver Decisiones).
- Botón para mostrar y ocultar los cuadrados a voluntad (opción descartada: ver Decisiones).
- Mover o redimensionar el overlay con el teclado.
- Persistir posición y tamaño del overlay entre sesiones.
- Varios overlays simultáneos.
- Cambiar `POLL_INTERVAL_MS` o exponerlo en Configuración.

## Modelo de datos

**`config.json`** — dos claves nuevas junto a las existentes:

```json
{
  "hotkey_toggle": "Ctrl+Shift+P",
  "hotkey_close": "Ctrl+Shift+Q"
}
```

- `hotkey_toggle`: string en notación `QKeySequence` (ej. `"Ctrl+Shift+P"`). Pausa/reanuda la transcripción si el overlay existe; si no existe, activa la selección y arranca la transcripción. Default `"Ctrl+Shift+P"`.
- `hotkey_close`: string en notación `QKeySequence`. Cierra el overlay si existe; sin overlay no hace nada. Default `"Ctrl+Shift+Q"`.
- Ambas combinaciones deben incluir al menos un modificador (`Ctrl`, `Alt` o `Shift`); se valida antes de guardar, nunca se persiste una combinación sin modificador.

**`model/hotkey_model.py`** (nuevo, no importa PySide6 ni `ctypes`):

- `MODIFIER_TOKENS = {"Ctrl", "Alt", "Shift", "Meta"}` — tokens de modificador reconocidos en la notación `QKeySequence`.
- `has_modifier(sequence_text: str) -> bool` — indica si `sequence_text` (ej. `"Ctrl+Shift+P"`) incluye al menos un modificador, comparando contra `MODIFIER_TOKENS` sobre las partes separadas por `+`.
- `parse_virtual_key(sequence_text: str) -> tuple[int, int]` — traduce la notación `QKeySequence` a `(modifiers, virtual_key)` en los códigos que espera `RegisterHotKey` de la API de Windows (`MOD_CONTROL`, `MOD_ALT`, `MOD_SHIFT`, `MOD_WIN` combinados con OR, más el código de tecla virtual). Lanza `ValueError` si `sequence_text` no tiene modificador o la tecla final no es reconocible.

**`controller/global_hotkeys.py`** (nuevo):

- `GlobalHotkeyManager(QObject)` — envuelve `RegisterHotKey`/`UnregisterHotKey` de `user32.dll` vía `ctypes.windll` e instala un `QAbstractNativeEventFilter` sobre `QApplication` para capturar el mensaje `WM_HOTKEY`.
- `register(hotkey_id: int, sequence_text: str) -> bool` — registra la combinación; devuelve `False` (sin lanzar excepción) si Windows la rechaza porque otra aplicación ya la tiene tomada.
- `unregister(hotkey_id: int) -> None` — libera una combinación previamente registrada.
- Señal `triggered(int)` — emite el `hotkey_id` cuando `WM_HOTKEY` llega para ese id.
- En un sistema operativo distinto de Windows, `register()` devuelve `False` siempre sin intentar cargar `ctypes.windll` (que no existe fuera de Windows), y la aplicación sigue funcionando solo con los botones.

**`view/screen_overlay.py`** — cambios:

- Se elimina el pintado de `_handle_rects()` en `paintEvent` (el diccionario y `_handle_at` se conservan, siguen gobernando el área de agarre y el redimensionado).
- `mouseMoveEvent` actualiza `self.setCursor(...)` según `_handle_at(event.pos())`: `Qt.SizeFDiagCursor` en `top_left`/`bottom_right`, `Qt.SizeBDiagCursor` en `top_right`/`bottom_left`, `Qt.ArrowCursor` fuera de cualquier handle.
- Botones `_close_button`, `_toggle_button` pasan a `QSize(32, 32)`; nuevo `_translate_button` (32×32, deshabilitado por defecto) con el mismo patrón de creación/posicionamiento que los otros dos.
- Nuevo `_status_label` (`QLabel`) en la barra de control, a la izquierda de los botones, con el texto del estado vigente.
- `CONTROL_BAR_HEIGHT` sube de `28` a `40` para alojar los botones de 32 px con margen.
- Nuevo método `set_status(status: str) -> None` — actualiza `_status_label` con uno de los cuatro rótulos (`"Detenido"`, `"Transcribiendo"`, `"Analizando…"`, `"Pausado"`).
- Nuevo método `set_translate_enabled(enabled: bool) -> None` y `set_translate_active(active: bool) -> None`, análogos a `set_toggle_enabled`/`set_running`.
- Nueva señal `translate_toggle_requested`.
- Tooltips: `_toggle_button.setToolTip(...)` y `_close_button.setToolTip(...)` se recalculan cuando cambia el atajo configurado (nuevo método `set_hotkey_labels(toggle_text: str, close_text: str)`), interpolando el texto del atajo vigente.

**`view/live_ocr_view.py`** — nuevo `QLabel` de estado (`self.status_label`) junto al `transcription_button`, con el mismo texto que `ScreenOverlay.set_status`; nuevo método `set_status(status: str)`.

**`view/metro_style.py`** — nuevo selector `QLabel#liveStatusLabel` (mismo color de acento que el resto de los labels de estado) y ajuste de `QPushButton#overlayCloseButton`/`#overlayToggleButton` para el tamaño 32×32; nuevo `QPushButton#overlayTranslateButton` calcado de `#overlayToggleButton`.

**`view/settings_view.py`** — dos `QKeySequenceEdit` nuevos ("Atajo pausar/reanudar", "Atajo cerrar overlay"), en una sección "OCR en vivo · atajos globales", con un `QLabel` de aviso que aparece si la validación (`has_modifier`) o el registro en `GlobalHotkeyManager` fallan. Señales `hotkey_toggle_changed(str)` y `hotkey_close_changed(str)`.

**`model/config_model.py`** — nuevas funciones `save_hotkey_toggle(str)` y `save_hotkey_close(str)`, análogas a `save_min_word_confidence()`, más los `setdefault` correspondientes en `load_config()`.

**`controller/live_ocr_controller.py`** — nuevo estado `_status` (uno de los cuatro valores), actualizado en cada transición (`activate_selection` → Detenido, `toggle_transcription` arrancando → Transcribiendo, inicio de una transcripción real → Analizando…, resultado recibido → Transcribiendo, pausa → Pausado); cada cambio se propaga a `self.view.set_status(...)` y, si el overlay existe, a `self._overlay.set_status(...)`. Nuevo `GlobalHotkeyManager` instanciado en `__init__`, registrado con los valores de `config.json` al arrancar y re-registrado cuando `SettingsController` guarda un atajo nuevo. `translate_toggle_requested` del overlay y `translate_toggled` de la vista pasan por el mismo `on_translate_toggled`, y `_translation_active` se refleja en ambos widgets.

**`controller/settings_controller.py`** — conecta `hotkey_toggle_changed`/`hotkey_close_changed` a `save_hotkey_toggle`/`save_hotkey_close` y a `LiveOcrController` para re-registrar el atajo correspondiente, mostrando el aviso de la vista si el registro falla.

## Plan de implementación

1. **`model/hotkey_model.py` (nuevo módulo, aislado).** Crear `MODIFIER_TOKENS`, `has_modifier` y `parse_virtual_key`. Nada lo importa todavía.
   Prueba manual: `python -c "from model.hotkey_model import has_modifier, parse_virtual_key; print(has_modifier('Ctrl+Shift+P'), has_modifier('P')); print(parse_virtual_key('Ctrl+Shift+P'))"` imprime `True False` y una tupla de enteros. `python main.py` arranca igual que antes.

2. **`model/config_model.py`: las dos claves nuevas.** Agregar los `setdefault` en `load_config()` y `save_hotkey_toggle`/`save_hotkey_close`.
   Prueba manual: borrar `config.json`, correr la app, confirmar que se regenera con `hotkey_toggle`/`hotkey_close` en sus defaults y que el resto de claves sigue intacto.

3. **`view/screen_overlay.py`: quitar los handles pintados y agrandar botones.** Eliminar el dibujo de `_handle_rects()` en `paintEvent`, agregar el cambio de cursor en `mouseMoveEvent`, subir los botones existentes a 32×32 y `CONTROL_BAR_HEIGHT` a 40. Todavía sin botón de traducción ni de estado.
   Prueba manual: activar la selección en OCR en vivo, confirmar que ya no se ven los cuadrados de esquina pero que el cursor cambia a flecha diagonal al acercarse y que el redimensionado sigue funcionando igual; confirmar que los botones ✕/▶ son más grandes y fáciles de acertar con el mouse.

4. **`view/screen_overlay.py` + `view/live_ocr_view.py`: indicador de estado y botón de traducción (sin conectar lógica).** Agregar `_status_label`/`set_status`, `_translate_button`/`set_translate_enabled`/`set_translate_active`/`translate_toggle_requested` al overlay; agregar `status_label`/`set_status` a `LiveOcrView`. Agregar los selectores nuevos en `metro_style.py`.
   Prueba manual: confirmar visualmente que el overlay y la vista muestran un label de estado (aunque todavía no cambie) y que aparece el tercer botón junto a ✕/▶, deshabilitado. Alternar tema claro/oscuro.

5. **`controller/live_ocr_controller.py`: conectar estado y traducción del overlay.** Actualizar `_status` en cada transición y propagarlo a la vista y al overlay; conectar `translate_toggle_requested` del overlay al mismo `on_translate_toggled` que ya usa `LiveOcrView`, sincronizando ambos botones vía `set_translate_active`.
   Prueba manual: activar selección (Detenido), iniciar transcripción (Transcribiendo), observar "Analizando…" mientras corre una transcripción, pausar (Pausado); confirmar que overlay y vista siempre muestran el mismo estado. Activar traducción desde el botón del overlay y confirmar que el de la vista queda marcado también, y viceversa; confirmar que el botón de traducción del overlay está deshabilitado mientras la transcripción no corre.

6. **`controller/global_hotkeys.py` (nuevo) + registro al arrancar.** Crear `GlobalHotkeyManager`; instanciarlo en `LiveOcrController.__init__`, registrar `hotkey_toggle`/`hotkey_close` leídos de `config.json` y conectar `triggered` a pausar/reanudar y cerrar el overlay (o activar selección + arrancar si no existe overlay, para el toggle).
   Prueba manual: con la aplicación abierta y el foco en otra ventana (el navegador, por ejemplo), presionar `Ctrl+Shift+P` y confirmar que arranca la selección y la transcripción; presionarlo de nuevo y confirmar que pausa/reanuda; presionar `Ctrl+Shift+Q` y confirmar que cierra el overlay. Repetir con la ventana de la aplicación en foco.

7. **`view/settings_view.py` + `controller/settings_controller.py`: atajos configurables.** Agregar los dos `QKeySequenceEdit` con su validación (`has_modifier`) y las señales; conectar a `save_hotkey_toggle`/`save_hotkey_close` y a un nuevo método de `LiveOcrController` que reintenta el registro con la combinación nueva, mostrando el aviso si `GlobalHotkeyManager.register` devuelve `False`.
   Prueba manual: cambiar el atajo de pausar a una combinación libre, confirmar que el tooltip del overlay se actualiza y que la nueva combinación funciona; intentar guardar una combinación sin modificador y confirmar que se rechaza con aviso; intentar guardar una combinación ya tomada por otra aplicación (ej. `Ctrl+Alt+Del` no aplica, pero puede probarse con un atajo ya registrado por otra app abierta) y confirmar el aviso de registro fallido sin romper el atajo anterior.

8. **Verificación end-to-end y `CLAUDE.md`.** Recorrido completo: activar selección, iniciar transcripción con Tesseract y con Claude (si hay API key), traducir desde ambos botones, pausar/reanudar y cerrar con atajo y con botón, cambiar los atajos desde Configuración, alternar tema. Actualizar en `CLAUDE.md` la descripción de `screen_overlay.py`, `live_ocr_view.py`, `settings_view.py`, `live_ocr_controller.py`, `settings_controller.py`, los módulos nuevos (`hotkey_model.py`, `global_hotkeys.py`) y las claves nuevas de `config.json`.
   Prueba: recorrido manual + revisión de imports rotos.

## Criterios de aceptación

- [ ] El área capturada por `capture_geometry()` nunca contiene píxeles de los handles de redimensión: la imagen enviada al OCR queda limpia en las cuatro esquinas.
- [ ] El redimensionado del overlay desde las esquinas sigue funcionando igual que antes, con el cursor cambiando a flecha diagonal al pasar sobre la zona de agarre.
- [ ] Los botones ✕/▶/traducir del overlay miden 32×32 px y cada uno tiene un tooltip que nombra la acción y, cuando aplica, el atajo configurado.
- [ ] El overlay y `LiveOcrView` muestran siempre el mismo estado entre Detenido, Transcribiendo, Analizando… y Pausado.
- [ ] El botón de traducción del overlay y el de `LiveOcrView` están siempre sincronizados: activar uno activa el otro.
- [ ] El botón de traducción del overlay está deshabilitado mientras la transcripción no está corriendo.
- [ ] `Ctrl+Shift+P` (o el atajo configurado) pausa/reanuda la transcripción con la aplicación en foco o sin foco; si no hay overlay, lo crea y arranca la transcripción.
- [ ] `Ctrl+Shift+Q` (o el atajo configurado) cierra el overlay con la aplicación en foco o sin foco.
- [ ] Los atajos se editan desde Configuración con `QKeySequenceEdit`, se persisten en `config.json` y sobreviven a reiniciar la aplicación.
- [ ] Guardar un atajo sin modificador (`Ctrl`, `Alt` o `Shift`) se rechaza con un aviso, sin persistirse.
- [ ] Si Windows rechaza el registro de una combinación por estar tomada por otra aplicación, se muestra un aviso y la combinación anterior sigue activa.
- [ ] `model/hotkey_model.py` no importa PySide6.
- [ ] Cada paso del plan deja la app ejecutable con `python main.py` sin romper flujos existentes.
- [ ] `CLAUDE.md` queda actualizado con los módulos, vistas y claves nuevas.

## Decisions

- **Sí:** dejar de pintar los handles en vez de ocultarlos y volver a mostrarlos en cada poll. Cualquier variante de mostrar/ocultar introduce una ventana de tiempo donde el cuadrado está visible al capturar, o un parpadeo perceptible; no pintarlos nunca elimina el problema de raíz.
- **No:** capturar con margen y recortar/enmascarar los cuadrados de la imagen antes del OCR. Es más código para lograr el mismo resultado que simplemente no dibujarlos, y agrega una operación de recorte que puede desalinearse si cambia el tamaño de los handles.
- **No:** cuadrados por fuera del área de selección (opción evaluada en la ronda de preguntas). Agrega geometría extra y píxeles adicionales de overlay en pantalla sin resolver nada que la zona de agarre invisible no resuelva ya.
- **No:** botón para mostrar/ocultar los cuadrados a voluntad. Deja la limpieza de la captura en manos de que el usuario se acuerde de ocultarlos antes de transcribir; la zona de agarre invisible no depende de que nadie recuerde nada.
- **Sí:** atajos globales vía `RegisterHotKey`/`ctypes`, sin dependencia externa nueva. El proyecto evita módulos externos salvo necesidad estricta (`CLAUDE.md`), y la API de Windows ya es accesible desde la biblioteca estándar.
- **No:** atajos solo con foco en la app (`QShortcut`). El caso de uso central de OCR en vivo es trabajar en otra ventana mientras la transcripción corre atrás; un atajo que exige volver a la app pierde la mayor parte de su utilidad.
- **Sí:** atajos configurables desde Configuración, con `QKeySequenceEdit` en vez de texto libre. Evita combinaciones mal escritas y dos apps peleando por el mismo atajo se resuelve avisando en vez de fallar en silencio.
- **Sí:** atajos activos mientras la app está abierta (no solo con el overlay creado). El caso de uso más común es "quiero volver a capturar sin ir a buscar el botón", y eso solo tiene sentido si el atajo funciona también con el overlay cerrado.
- **Sí:** cuatro estados con "Analizando…" como estado propio. Da señal de vida en cada ciclo y hace visible cuándo el filtro de texto de la spec 16 está descartando capturas en vez de dejar la barra congelada en "Transcribiendo" todo el tiempo.
- **Sí:** botón de traducción como espejo del que ya existe en `LiveOcrView`, sin panel de traducción flotante junto al overlay. Reutiliza el estado y la lógica de la spec 11 sin agregar una superficie de UI nueva.
- **No:** exponer el intervalo de polling o mover/redimensionar el overlay por teclado. Ninguno de los dos se pidió y ambos abren su propia spec de alcance.
- **Sí:** atajos globales solo en Windows, sin implementación para macOS/Linux. `CLAUDE.md` no menciona soporte multiplataforma como requisito del proyecto y `RegisterHotKey` es la única vía sin dependencia externa disponible hoy.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| `RegisterHotKey` puede fallar si otra aplicación ya tiene registrada la misma combinación, incluso con la combinación por defecto (`Ctrl+Shift+P`/`Ctrl+Shift+Q`). | `register()` devuelve `False` sin lanzar excepción; se avisa una vez y la app sigue funcionando con los botones. El usuario puede cambiar el atajo desde Configuración. |
| Subir `CONTROL_BAR_HEIGHT` de 28 a 40 px agranda el overlay total y puede desalinear la posición guardada mentalmente por el usuario entre sesiones. | La posición nunca se persiste (fuera de alcance ya declarado en spec 08), así que cada activación empieza centrada con el nuevo tamaño; no hay estado previo que romper. |
| Un `QAbstractNativeEventFilter` mal instalado o no removido puede interferir con otros eventos nativos de Qt o quedar huérfano al cerrar la app. | Se instala una única vez en `LiveOcrController.__init__` (vida igual a la de la app) y se hace `UnregisterHotKey` explícito; se prueba el recorrido completo de cierre en el paso 8. |
| Confundir el atajo de pausar con el de activar selección (mismo atajo, comportamiento distinto según haya overlay o no) puede sorprender si el usuario esperaba que solo pausara. | Documentado explícitamente en el modelo de datos y probado en el paso 6; el tooltip del botón de la vista puede aclarar el doble comportamiento si la prueba manual lo amerita. |
