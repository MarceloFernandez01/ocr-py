# SPEC 09 — Separar activación de overlay e inicio de transcripción en OCR en vivo + labels de idioma

> **Status:** Implementado
> **Depends on:** `specs/08-ocr-en-vivo.md`
> **Date:** 2026-07-13
> **Objective:** Separar en dos botones independientes el flujo de "OCR en vivo" ("Activar selección" solo crea/reposiciona el overlay; "Iniciar transcripción" / "Pausar transcripción" controla el polling), y agregar un label "Idioma" sobre los selectores de idioma de `OcrView` y `LiveOcrView` para clarificar su propósito.

## Scope

**In:**

- **`view/live_ocr_view.py`**: nuevo botón `transcription_button` ("Iniciar transcripción" / "Pausar transcripción"), deshabilitado por defecto. Nueva señal `toggle_transcription_clicked`. Nuevos setters: `enable_transcription_button()`, `disable_transcription_button()`, `set_transcription_button_running(running: bool)`. `activate_selection_clicked` sin cambios. Se agrega un `QLabel("Idioma")` arriba de `language_combobox` (envolviendo en un layout vertical dentro de la toolbar existente). Para que `activate_button` y `transcription_button` queden alineados verticalmente con el combobox (que ahora tiene el label arriba), se envuelve cada botón en su propio `QVBoxLayout` con un `QLabel("")` vacío arriba (mismo alto que el label "Idioma", sin texto).
- **`view/ocr_view.py`**: se agrega un `QLabel("Idioma")` arriba de `language_combobox`, mismo criterio visual que en `LiveOcrView`. Por el mismo motivo de alineación, `transcribe_button` (que comparte `right_toolbar` con el combobox) se envuelve también en un `QVBoxLayout` con un `QLabel("")` vacío arriba. `open_button` también se envuelve en `QVBoxLayout` con `QLabel("")` vacío arriba, para quedar a la misma altura que el resto de la toolbar (aunque esté solo en `left_toolbar`, sin combobox al lado).
- **Convención general (no exclusiva de esta spec):** todo botón fuera del sidebar se envuelve en un `QVBoxLayout` con un `QLabel("")` vacío arriba, salvo indicación explícita en contrario. Esto asegura que cualquier fila de controles quede alineada verticalmente aunque algunos elementos tengan label de texto y otros no.
- **`controller/live_ocr_controller.py`**: se separa `start()` en `activate_selection()` (crea o recrea el overlay en posición/tamaño default, detiene polling en curso si lo había, nunca arranca el `QTimer`) y `toggle_transcription()` (arranca o detiene el `QTimer` según el estado actual, sin tocar el overlay). `_on_overlay_closed()` deshabilita `transcription_button` y lo deja en label "Iniciar transcripción". `geometry_changed` del overlay solo dispara `_poll()` si el polling está activo.
- **`view/metro_style.py`**: estilo del nuevo botón `transcription_button` (mismo patrón que los `QPushButton` existentes) y del nuevo `QLabel` "Idioma" (tipografía chica/secundaria, sin romper la estética Metro), en ambos temas. La verificación visual final (contraste, alineación) queda para el paso de verificación de `/spec-impl`.

**Out:**

- No se toca `ScreenOverlay`, `model/image_diff.py` ni `model/ocr_model.py`.
- No se agrega un tercer estado visual al botón toggle (solo alterna texto entre dos labels).
- No se persiste el estado de pausa/corriendo entre navegaciones de sidebar (navegar afuera sigue llamando `stop()` completo).
- No se agregan labels con texto a otros controles (combobox de motor OCR en Configuración, etc.), solo a los dos selectores de idioma existentes. Los labels vacíos espaciadores sobre `activate_button`, `transcription_button` y `transcribe_button` son puramente de alineación visual, no cuentan como "agregar un label" con contenido.
- No se cambia el comportamiento de "OCR de imágenes" más allá del label agregado.

## Data model

No aplica: esta spec no introduce nuevas estructuras de datos ni cambios en `config.json`.

## Implementation plan

1. **`view/live_ocr_view.py`: nuevo botón toggle y label "Idioma".** Agregar `QLabel("Idioma")` envolviendo `language_combobox` en un `QVBoxLayout` (label arriba, combobox abajo) dentro de la toolbar existente. Agregar `self.transcription_button = QPushButton("Iniciar transcripción")`, `setEnabled(False)` inicial, señal `toggle_transcription_clicked` conectada a su `clicked`. Métodos `enable_transcription_button()`, `disable_transcription_button()`, `set_transcription_button_running(running: bool)` (alterna texto entre "Pausar transcripción" y "Iniciar transcripción"). Envolver `activate_button` y `transcription_button` cada uno en su propio `QVBoxLayout` con un `QLabel("")` vacío arriba, para que ambos queden alineados verticalmente con `language_combobox`.
   Prueba manual: instanciar `LiveOcrView` sola, confirmar que aparece el label "Idioma", el botón nuevo deshabilitado con texto "Iniciar transcripción", que los tres controles (combobox, "Activar selección", "Iniciar transcripción") quedan alineados en la misma fila, y que los setters cambian estado/texto sin explotar.

2. **`view/ocr_view.py`: label "Idioma".** Mismo cambio de layout (label arriba del combobox) sin tocar el resto de `OcrView`. Envolver `transcribe_button` en un `QVBoxLayout` con un `QLabel("")` vacío arriba, para que quede alineado con el combobox dentro de `right_toolbar`. Envolver también `open_button` (en `left_toolbar`) en un `QVBoxLayout` con `QLabel("")` vacío arriba, por la convención general de alineación.
   Prueba manual: instanciar `OcrView` sola, confirmar visualmente que aparece "Idioma" arriba del selector, que "Abrir imagen" y "Transcribir" quedan alineados a la misma altura que el combobox, y que el layout existente no se rompe.

3. **`view/metro_style.py`: estilos del label y del botón toggle.** Agregar regla para el nuevo `QLabel` (tipografía secundaria/chica, sin competir visualmente con el resto) y confirmar que `transcription_button` hereda el estilo ya definido para `QPushButton` (agregar selector específico solo si hace falta diferenciarlo de "Activar selección"), en ambos temas.
   Prueba manual: alternar tema en Configuración, confirmar que el label y el botón se ven legibles y consistentes en claro/oscuro.

4. **`controller/live_ocr_controller.py`: separar `start()` en `activate_selection()` y `toggle_transcription()`.**
   - `activate_selection()` (reemplaza la conexión a `activate_selection_clicked`): si `self._overlay` existe, lo destruye (desconectando señales, deteniendo timer/counter si corrían) antes de crear uno nuevo; siempre crea `ScreenOverlay` en posición/tamaño default, conecta `closed`/`geometry_changed`, resetea `self._previous_capture = None`, y llama a `self.view.enable_transcription_button()` + `self.view.set_transcription_button_running(False)`. **No** arranca `QTimer` ni llama a `_poll()`.
   - `toggle_transcription()` (conectado a `toggle_transcription_clicked`): si `self._timer` es `None`, resuelve `tesseract_path` (mismo flujo de `_prompt_tesseract_path()` que hoy), crea y arranca el `QTimer`, llama a `_poll()` inicial, y `set_transcription_button_running(True)`; si `self._timer` ya existe, lo detiene y pone `set_transcription_button_running(False)` (sin tocar el overlay ni `self._previous_capture`).
   - `_on_overlay_closed()`: agregar `self.view.disable_transcription_button()` y `self.view.set_transcription_button_running(False)`.
   - `geometry_changed` sigue conectada a `_poll()`, pero `_poll()` agrega un guard: si `self._timer is None`, retorna sin capturar.
   - `stop()` (usado por `MainWindow` al navegar afuera) se mantiene igual, pero además debe dejar el botón en el mismo estado que `_on_overlay_closed()` (deshabilitado, label "Iniciar transcripción").
   Prueba manual: activar OCR en vivo, confirmar que al crear el overlay el polling NO arranca solo; mover/redimensionar el overlay y confirmar que no dispara capturas; clickear "Iniciar transcripción" y confirmar que arranca el polling y el botón pasa a "Pausar transcripción"; clickear "Pausar transcripción" y confirmar que se detiene sin cerrar el overlay; clickear "Activar selección" con el overlay ya abierto y confirmar que lo recrea centrado y detiene cualquier polling en curso; cerrar con la X mientras corre y confirmar que el botón vuelve a "Iniciar transcripción" deshabilitado.

5. **Verificación end-to-end.** Recorrido manual completo: activar selección → mover overlay sin que capture nada → iniciar transcripción → pausar → reanudar → recrear overlay con "Activar selección" → cerrar con X → repetir. Confirmar que "OCR de imágenes" sigue funcionando con el nuevo label "Idioma" sin regresiones, y revisión visual de ambos temas para el label y el botón nuevo.
   Prueba: recorrido manual + revisión de imports rotos.

## Acceptance criteria

- [x] En `LiveOcrView`, al entrar a la vista sin overlay creado, "Iniciar transcripción" aparece deshabilitado.
- [x] Clickear "Activar selección" crea el overlay y habilita "Iniciar transcripción" (label "Iniciar transcripción"), sin arrancar el polling.
- [x] Mover o redimensionar el overlay antes de clickear "Iniciar transcripción" no dispara ninguna captura ni transcripción.
- [x] Clickear "Iniciar transcripción" arranca el polling, el botón cambia a label "Pausar transcripción", y el ciclo de captura/diff/transcripción funciona igual que antes (spec 08).
- [x] Clickear "Pausar transcripción" detiene el polling sin cerrar el overlay; el overlay se puede seguir moviendo/redimensionando, y el botón vuelve a label "Iniciar transcripción".
- [x] Clickear "Iniciar transcripción" de nuevo tras una pausa retoma el polling desde la posición/tamaño actual del overlay.
- [x] Clickear "Activar selección" con el overlay ya abierto lo destruye y recrea en posición/tamaño default, deteniendo cualquier polling en curso y dejando "Iniciar transcripción" habilitado en su label inicial.
- [x] Cerrar el overlay con la X (esté corriendo o pausado) detiene el polling, deshabilita "Iniciar transcripción" y lo deja en label "Iniciar transcripción".
- [x] Navegar afuera de "OCR en vivo" (`stop()`) deja el mismo estado que al cerrar con la X: overlay destruido, botón deshabilitado en label "Iniciar transcripción".
- [x] `OcrView` y `LiveOcrView` muestran un label "Idioma" arriba de cada selector de idioma, legible y sin romper la estética Metro en ambos temas (claro/oscuro).
- [x] El flujo de "OCR de imágenes" (specs 01-03) sigue funcionando sin regresiones.
- [x] MVC respetado: los cambios de estado de botones siguen viviendo en el Controller (la vista solo expone señales y setters, sin lógica de negocio).

## Decisions

- **Sí:** separar "Activar selección" (overlay) de "Iniciar transcripción" (polling) en dos controles independientes, en vez de mantenerlos fusionados. Arrastrar/redimensionar el overlay resultaba molesto porque el polling ya corría mientras se acomodaba el recuadro.
- **Sí:** el botón de transcripción es un toggle único ("Iniciar transcripción" ↔ "Pausar transcripción") en vez de dos botones separados de iniciar/detener. Evita duplicar controles cuando el estado es binario y mutuamente excluyente.
- **Sí:** "Activar selección" se mantiene siempre habilitado, incluso con el overlay ya abierto; al reclickearlo recrea el overlay en posición/tamaño default (en vez de no-op). Le da al usuario una forma explícita de "resetear" el overlay si lo perdió de vista, sin necesidad de cerrar con la X primero.
- **Sí:** `geometry_changed` del overlay solo dispara `_poll()` si el polling está activo. Si no, mover/redimensionar el overlay antes de arrancar la transcripción no debe generar capturas ni transcripciones fantasma.
- **Sí:** pausar la transcripción no oculta ni destruye el overlay ni limpia la miniatura/texto ya mostrados; solo detiene el `QTimer`. Mantiene la última información visible mientras el usuario reposiciona el overlay con calma.
- **Sí:** cerrar el overlay con la X siempre deshabilita "Iniciar transcripción" y lo resetea a su label inicial, sin importar si estaba corriendo o pausado. Sin overlay no hay geometría que capturar, así que no tiene sentido dejarlo habilitado.
- **Sí:** agregar el label "Idioma" arriba de ambos selectores de idioma (`OcrView` y `LiveOcrView`) en la misma spec, aunque el objetivo central sea otro. Es un cambio chico y visual que no amerita una spec separada.
- **No:** agregar un tercer estado visual al botón toggle (ej. color distinto para "pausado" vs "nunca iniciado"). Alcanza con alternar el texto entre dos labels; no se pidió diferenciación visual adicional.
- **No:** persistir si la transcripción quedó pausada o corriendo al navegar fuera de "OCR en vivo". `stop()` sigue reseteando todo el estado, como ya definía spec 08.
- **Sí:** por defecto, las pruebas manuales de cada paso del plan de implementación las ejecuta el usuario, no el asistente; el asistente solo verifica por otros medios (lectura de código, `grep`, chequeo de imports) cuando el usuario no pueda evaluar el cambio corriendo el proyecto. Esto es el default, no una prohibición absoluta: si el usuario pide explícitamente que el asistente corra la app y valide los pasos, el asistente puede hacerlo (ej. con la skill `run`), dejando aclarado en la respuesta qué pudo verificar de forma automática y qué sigue requiriendo confirmación visual/manual del usuario.
