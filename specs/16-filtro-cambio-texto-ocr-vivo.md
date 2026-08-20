# Spec 16: Filtro de cambio de texto en OCR en vivo, motor Claude Haiku y medidor de consumo

**Estado:** Aprobado
**Dependencias:** `specs/08-ocr-en-vivo.md` (ciclo de polling y diff de píxeles), `specs/09-live-ocr-boton-iniciar-transcripcion.md`, `specs/11-traduccion-ocr-en-vivo.md` (traducción encadenada al resultado), `specs/13-ocr-claude-motor-alternativo.md` (motor Claude, clave `engine`, API key en keyring; esta spec levanta su exclusión de OCR en vivo), `specs/15-filtro-confianza-palabra-ocr.md` (patrón de control en Configuración persistido en `config.json`)
**Fecha:** 2026-08-19

**Objetivo:** Evitar transcripciones y llamadas redundantes en OCR en vivo comparando el texto reconocido entre capturas —con Tesseract local como filtro previo gratuito— y habilitar Claude Haiku como motor de OCR en vivo detrás de ese filtro, un cooldown configurable y un medidor de consumo en la barra inferior de la aplicación.

## Contexto

Hoy `controller/live_ocr_controller.py` dispara una transcripción cada vez que `model/image_diff.py::has_changed` detecta una diferencia media de píxeles mayor a `0.02` entre dos capturas (`_poll`, cada 1500 ms). Ese diff es de **píxeles**, no de **texto**: un cursor parpadeante, una animación, una sombra o el ruido de compresión de un video ya lo disparan. Con Tesseract eso solo cuesta CPU y hace parpadear el resultado; en cuanto Claude Haiku entre al ciclo en vivo, cada falso positivo es una llamada paga. La spec 13 dejó OCR en vivo explícitamente fuera del alcance de Claude por ese motivo; esta spec construye el filtro que faltaba y recién entonces habilita el motor.

**Restricción técnica verificada** (documentación de Anthropic, consultada el 2026-08-19): la API **no expone el crédito restante** de una API key. `GET /v1/organizations/cost_report` (Admin API) informa gasto consumido y exige una credencial de administración de la organización, no la API key `sk-ant-api...` que la app guarda; los headers `anthropic-ratelimit-*-remaining` miden cuota de tasa por minuto, no dinero. Por eso el medidor pedido se construye como **consumo propio acumulado**, calculado desde `usage.input_tokens`/`usage.output_tokens` que devuelve cada respuesta, por el pricing de Claude Haiku 4.5 ($1.00/MTok de entrada, $5.00/MTok de salida).

## Alcance

**Dentro del alcance:**

- Nuevo módulo `model/text_diff.py`: comparación de dos transcripciones por umbral de similitud (`difflib.SequenceMatcher`, biblioteca estándar — sin dependencia externa nueva) sobre texto normalizado.
- Cascada de filtros en `_poll()` de `controller/live_ocr_controller.py`: diff de píxeles (`has_changed`, ya existente) → transcripción con Tesseract → comparación de texto (`has_text_changed`) → recién ahí, refresco de la UI y/o llamada a Claude.
- El filtro de texto actúa con cualquier motor: con Tesseract puro evita refrescar el panel de resultado y re-disparar la traducción (spec 11) cuando el texto es equivalente al anterior.
- Habilitar Claude Haiku como motor de OCR en vivo, reutilizando `transcribe_image_claude` de `model/claude_ocr_model.py`, gobernado por la clave `engine` existente más un interruptor de opt-in propio del vivo (`live_claude_enabled`).
- Con Claude activo, el texto de Tesseract se usa **solo** como detector interno de cambio; el panel de resultado muestra únicamente transcripciones de Claude.
- Cooldown configurable: tiempo mínimo entre dos llamadas a Claude. Un cambio de texto detectado durante el cooldown queda **pendiente** y se envía al vencer, no se pierde.
- Nuevo módulo `model/claude_usage_model.py`: costo por llamada a partir de los tokens reales que devuelve la API y acumulación del gasto mensual en `config.json`.
- Nueva barra inferior permanente (`view/spend_meter_view.py`), visible en toda la aplicación cuando el motor es Claude y hay API key guardada: barra de progreso de gasto del mes contra un presupuesto configurable, monto consumido y cantidad de llamadas.
- Aviso único al cruzar el presupuesto mensual configurado (la barra pasa a estado de alerta); las llamadas **no** se bloquean.
- Cinco controles nuevos en Configuración, persistidos en `config.json`: interruptor "Usar Claude también en OCR en vivo", umbral de similitud de texto, sensibilidad del diff de píxeles, cooldown en segundos y presupuesto mensual en USD.
- Manejo de errores de la API de Claude en el ciclo en vivo: se detiene el polling y se avisa una sola vez, en vez de repetir el error en cada tick.
- `transcribe_image_claude` pasa a devolver también los tokens consumidos; se actualiza su único llamador actual (`controller/ocr_controller.py`) para registrar el gasto también en OCR de imágenes.
- Actualizar `CLAUDE.md` (hoy documenta que OCR en vivo usa Tesseract exclusivamente).

**Fuera del alcance:**

- Consultar el saldo o crédito real de la cuenta de Anthropic: la API no lo expone (ver Contexto). El medidor refleja el consumo generado por esta app, no el de la organización.
- Admin API (`/v1/organizations/cost_report`) y la credencial de administración que requiere.
- Bloquear las llamadas al alcanzar el presupuesto: el medidor avisa, no frena.
- Traducción con Claude: sigue vía `argostranslate` (spec 11), independiente del motor OCR.
- Preprocesamiento o tiling para el flujo Claude en vivo — igual que en spec 13, se envía la captura completa.
- Contador propio dentro de `LiveOcrView`: lo absorbe la barra inferior global, `view/live_ocr_view.py` no se modifica.
- Cambiar el intervalo de polling (`POLL_INTERVAL_MS`, hoy fijo en 1500 ms) o exponerlo en Configuración.
- Detección de región de texto dentro de la captura (OCR selectivo por zona).
- Aplicar el filtro de similitud a OCR de imágenes estático: es un flujo manual disparado por el usuario, sin polling ni repetición.
- Historial de gasto por día o por mes anterior: se guarda únicamente el acumulado del mes en curso.

## Modelo de datos

**`config.json`** — seis claves nuevas junto a las existentes:

```json
{
  "tesseract_path": "...",
  "theme": "dark",
  "engine": "tesseract",
  "min_word_confidence": 95,
  "live_claude_enabled": false,
  "text_similarity_threshold": 90,
  "pixel_change_sensitivity": 2,
  "claude_cooldown_seconds": 10,
  "claude_monthly_budget_usd": 5.0,
  "claude_spend": { "month": "2026-08", "usd": 0.0, "calls": 0 }
}
```

- `live_claude_enabled`: booleano (default `false`). Solo tiene efecto si `engine` es `"claude"`. Con `false`, OCR en vivo usa Tesseract sin importar el motor configurado (comportamiento idéntico al actual).
- `text_similarity_threshold`: entero 0-100 (default `90`). Dos textos se consideran **iguales** si su similitud normalizada es mayor o igual a este valor. `0` desactiva el filtro (todo cambio de píxeles pasa, comportamiento previo a esta spec).
- `pixel_change_sensitivity`: entero 0-100 (default `2`), en centésimas de diferencia media de píxeles. Se pasa como `threshold` a `has_changed` dividido por 100, de modo que el default `2` reproduce exactamente el `CHANGE_THRESHOLD = 0.02` actual.
- `claude_cooldown_seconds`: entero 1-120 (default `10`). Tiempo mínimo entre dos llamadas a Claude en OCR en vivo.
- `claude_monthly_budget_usd`: número (default `5.0`). Referencia del medidor; solo informa, no bloquea.
- `claude_spend`: objeto acumulador con `month` (`"YYYY-MM"`), `usd` (acumulado del mes) y `calls` (llamadas del mes). Si `month` no coincide con el mes actual al registrar una llamada, se reinicia a cero antes de sumar.

**`model/text_diff.py`** (nuevo, no importa PySide6):

- `normalize_text(text: str) -> str` — colapsa espacios y saltos de línea repetidos y recorta bordes, para que diferencias de espaciado no cuenten como cambio.
- `has_text_changed(previous: str | None, current: str, threshold: int) -> bool` — `previous is None` devuelve `True`; `threshold == 0` devuelve `True` siempre (filtro desactivado); en el resto de los casos devuelve `True` cuando `SequenceMatcher(None, normalize_text(previous), normalize_text(current)).ratio() * 100 < threshold`.

**`model/claude_usage_model.py`** (nuevo, no importa PySide6 ni el SDK `anthropic`):

- `HAIKU_INPUT_USD_PER_MTOK = 1.00` y `HAIKU_OUTPUT_USD_PER_MTOK = 5.00` — pricing vigente de Claude Haiku 4.5, con comentario indicando que es un valor cacheado que puede cambiar.
- `call_cost_usd(input_tokens: int, output_tokens: int) -> float` — costo exacto de una llamada.
- `register_call(input_tokens: int, output_tokens: int) -> dict` — reinicia `claude_spend` si cambió el mes, suma el costo y una llamada, persiste en `config.json` y devuelve el acumulador actualizado.
- `load_spend() -> dict` — devuelve el acumulador del mes en curso (reiniciado en memoria si el mes cambió), para pintar la barra al arrancar.

**`model/claude_ocr_model.py`** — cambio de firma:

- `transcribe_image_claude(image, language_code, api_key) -> tuple[str, int, int]`: devuelve `(texto, input_tokens, output_tokens)` leídos de `response.usage`. Único llamador actual: `controller/ocr_controller.py`, que se actualiza en el mismo paso.

**`model/config_model.py`** — nuevas funciones `save_live_claude_enabled(bool)`, `save_text_similarity_threshold(int)`, `save_pixel_change_sensitivity(int)`, `save_claude_cooldown_seconds(int)`, `save_claude_monthly_budget_usd(float)` y `save_claude_spend(dict)`, todas análogas a `save_min_word_confidence()`, más los `setdefault` correspondientes en `load_config()`.

**`view/settings_view.py`** — cinco controles nuevos y sus señales:

- Interruptor `ThemeSwitch` reutilizado (mismo widget, otro rótulo) "Usar Claude también en OCR en vivo", visible solo con motor Claude, junto a un texto de advertencia de costo del polling. Señal `live_claude_toggled(bool)`.
- `QSlider` 0-100 "Sensibilidad al cambio de texto" con etiqueta numérica. Señal `text_similarity_threshold_changed(int)`.
- `QSlider` 0-100 "Sensibilidad al cambio de imagen" con etiqueta numérica. Señal `pixel_change_sensitivity_changed(int)`.
- `QSlider` 1-120 "Tiempo mínimo entre llamadas a Claude (s)" con etiqueta numérica, visible solo con motor Claude. Señal `claude_cooldown_changed(int)`.
- `QLineEdit` numérico "Presupuesto mensual (USD)", visible solo con motor Claude. Señal `claude_budget_changed(float)`.

**`view/spend_meter_view.py`** (nuevo) — `SpendMeterView(QWidget)`: franja horizontal de ~28 px con `QProgressBar` y `QLabel`, sin lógica de negocio.

- `set_spend(usd: float, calls: int, budget_usd: float)` — pinta "Claude · 14 llamadas · $0.42 de $5.00" y el progreso correspondiente.
- `set_over_budget(over: bool)` — estado de alerta visual al superar el presupuesto.

**`view/main_window.py`** — el `central_widget` pasa de `QHBoxLayout` a un `QVBoxLayout` que contiene la fila actual (sidebar + separador + stack) y debajo la `SpendMeterView`. Nuevo método `refresh_spend_meter()` que consulta `load_spend()` + `load_config()` y decide visibilidad (visible solo si `engine == "claude"` y hay API key en el keyring), invocado al arrancar, tras cada llamada registrada y al cambiar el motor desde Configuración.

**`controller/settings_controller.py`** — conecta las cinco señales nuevas a sus `save_*`, y llama a `MainWindow.refresh_spend_meter()` al cambiar el motor o guardar la API key.

**`controller/live_ocr_controller.py`** — estado nuevo: `_last_detector_text` (último texto de Tesseract aceptado), `_last_claude_call` (marca de tiempo monotónica), `_pending_capture` (captura cuya llamada quedó diferida por cooldown) y los valores de configuración leídos al arrancar el polling.

**`controller/ocr_controller.py`** — desempaqueta la nueva tupla de `transcribe_image_claude` y registra el gasto vía `register_call`.

## Plan de implementación

Cada paso deja la app ejecutable con `python main.py`, sin romper flujos existentes hasta el paso siguiente. El orden va de "aislado y sin conectar" a "conectado e integrado".

1. **`model/text_diff.py` (nuevo módulo, aislado).** Crear `normalize_text` y `has_text_changed` según el modelo de datos. Nada lo importa todavía.
   Prueba manual: `python -c "from model.text_diff import has_text_changed; print(has_text_changed('hola  mundo', 'hola mundo', 90), has_text_changed('hola mundo', 'chau mundo', 90))"` imprime `False True`. `python main.py` arranca igual que antes.

2. **`model/config_model.py`: las seis claves nuevas.** Agregar los `setdefault` en `load_config()` y las funciones `save_*` correspondientes.
   Prueba manual: borrar `config.json`, correr la app, confirmar que se regenera con las seis claves en sus valores por defecto y que `tesseract_path`/`theme`/`engine`/`min_word_confidence` siguen intactos al cerrar.

3. **`view/settings_view.py`: los cinco controles (sin conectar lógica).** Agregar los widgets, su visibilidad condicional al motor Claude (extendiendo `_update_engine_visibility`) y las señales. Las señales se emiten pero nadie las escucha todavía.
   Prueba manual: ir a Configuración con motor Tesseract y confirmar que solo aparecen los dos deslizadores de sensibilidad; cambiar a Claude Haiku y confirmar que aparecen además el interruptor de OCR en vivo, el cooldown y el presupuesto. Confirmar que mover los controles no cambia ningún comportamiento todavía y que tema, motor y API key siguen funcionando igual.

4. **`controller/settings_controller.py`: conectar los cinco controles.** Persistir cada valor con su `save_*`.
   Prueba manual: mover cada control, cerrar y reabrir la app, confirmar que los cinco conservan el valor (persistencia en `config.json`).

5. **`controller/live_ocr_controller.py`: filtro de texto con Tesseract (todavía sin Claude).** Leer `text_similarity_threshold` y `pixel_change_sensitivity` al arrancar el polling; pasar la sensibilidad a `has_changed` (dividida por 100) y, tras cada resultado de Tesseract, comparar contra `_last_detector_text` con `has_text_changed`: si es equivalente, descartar el resultado sin tocar la vista ni disparar traducción; si cambió, actualizar el texto mostrado y `_last_detector_text` como hoy.
   Prueba manual: capturar una región estática con un cursor parpadeante o una animación menor y confirmar que el panel de resultado ya no parpadea ni la traducción se re-dispara. Capturar una región donde el texto sí cambia y confirmar que el resultado se actualiza. Bajar el umbral de similitud a `0` en Configuración y confirmar que vuelve el comportamiento previo a esta spec.

6. **`model/claude_usage_model.py` + tokens reales + registro en OCR de imágenes.** Crear el módulo de costo/acumulación; cambiar `transcribe_image_claude` para devolver `(texto, input_tokens, output_tokens)`; actualizar `controller/ocr_controller.py` para desempaquetar la tupla y llamar a `register_call`. El gasto ya se acumula, todavía sin UI que lo muestre.
   Prueba manual: con motor Claude, transcribir una imagen y confirmar que el texto sigue apareciendo igual que antes y que `config.json` ganó un `claude_spend` con `calls: 1` y un `usd` distinto de cero y plausible. Repetir y confirmar que suma.

7. **`view/spend_meter_view.py` + integración en `MainWindow`.** Crear la franja inferior, reacomodar el layout central a `QVBoxLayout`, agregar `refresh_spend_meter()` y llamarlo al arrancar, después de cada `register_call` y desde `SettingsController` al cambiar motor o API key. Estado de alerta y aviso único al cruzar el presupuesto.
   Prueba manual: con motor Tesseract, confirmar que la barra no aparece y que la ventana se ve como antes. Cambiar a Claude con API key cargada y confirmar que aparece abajo con el acumulado del paso 6. Transcribir una imagen y confirmar que el monto y el contador suben al instante. Bajar el presupuesto por debajo del gasto acumulado y confirmar el estado de alerta y el aviso una sola vez. Alternar tema claro/oscuro con la barra visible.

8. **`controller/live_ocr_controller.py`: motor Claude en el ciclo en vivo.** Con `engine == "claude"` y `live_claude_enabled`, cuando el filtro de texto detecta un cambio real: si pasó el cooldown desde `_last_claude_call`, lanzar `transcribe_image_claude` en el `QThreadPool` (mismo patrón de `QRunnable` + señales ya usado) y mostrar solo su resultado; si no pasó, guardar la captura en `_pending_capture` y despacharla en el primer `_poll` posterior al vencimiento. Registrar cada llamada con `register_call` y refrescar el medidor. Ante error de la API, detener el polling y mostrar un `QMessageBox` una sola vez.
   Prueba manual: con Claude y el interruptor de vivo encendidos, capturar una región de texto estático y confirmar que tras la primera transcripción no se hacen más llamadas (el contador de la barra no sube) aunque haya ruido visual. Cambiar el texto de la región y confirmar que se hace exactamente una llamada más. Cambiar el texto varias veces seguidas dentro del cooldown y confirmar que se hace una sola llamada al vencer, con el contenido más reciente. Desconectar la red y confirmar que el polling se detiene con un único aviso. Apagar el interruptor y confirmar que el vivo vuelve a Tesseract aunque el motor siga en Claude.

9. **Verificación end-to-end y `CLAUDE.md`.** Recorrido completo con ambos motores, con y sin traducción activa, navegando entre vistas y reiniciando la app. Actualizar en `CLAUDE.md` la descripción de `live_ocr_controller.py`, la nota de spec 13 sobre el uso exclusivo de Tesseract en vivo, las claves de `config.json` y los módulos/vistas nuevos.
   Prueba: recorrido manual + revisión de imports rotos.

## Criterios de aceptación

- [ ] `model/text_diff.py` existe, no importa PySide6, y `has_text_changed` devuelve `False` para dos textos que solo difieren en espaciado y `True` cuando la similitud cae por debajo del umbral.
- [ ] `config.json` incluye las seis claves nuevas con sus defaults; un `config.json` previo a esta spec se migra al abrir la app sin perder `tesseract_path`/`theme`/`engine`/`min_word_confidence`.
- [ ] Con `pixel_change_sensitivity` en `2` (default), el diff de píxeles se comporta exactamente como el `CHANGE_THRESHOLD = 0.02` actual.
- [ ] En OCR en vivo con Tesseract, una región cuyo contenido visual cambia pero cuyo texto no (cursor, animación, ruido de video) deja de refrescar el panel de resultado y deja de re-disparar la traducción.
- [ ] Con `text_similarity_threshold` en `0`, el comportamiento de OCR en vivo es idéntico al previo a esta spec.
- [ ] Con `engine: "claude"` y `live_claude_enabled: false`, OCR en vivo sigue usando Tesseract — sin regresión respecto de la spec 13.
- [ ] Con `engine: "claude"` y `live_claude_enabled: true`, una región de texto estático genera exactamente una llamada a Claude, sin importar cuántos ciclos de polling pasen ni cuánto ruido visual haya.
- [ ] Con Claude activo en vivo, el panel de resultado nunca muestra texto de Tesseract: solo el contador de segundos mientras espera y la transcripción de Claude al llegar.
- [ ] Dos cambios de texto dentro del cooldown producen una sola llamada, disparada al vencer y con el contenido más reciente.
- [ ] Un error de la API durante el ciclo en vivo detiene el polling y muestra un único `QMessageBox`, sin repetirlo en cada tick ni caer a Tesseract en silencio.
- [ ] `transcribe_image_claude` devuelve los tokens de entrada y salida reales, y cada llamada (desde OCR de imágenes o desde OCR en vivo) queda registrada en `claude_spend` de `config.json`.
- [ ] El acumulado `claude_spend` se reinicia solo al registrar la primera llamada de un mes calendario nuevo.
- [ ] La barra inferior aparece únicamente con `engine: "claude"` y API key guardada; con Tesseract la ventana se ve como antes de esta spec.
- [ ] La barra muestra llamadas, monto consumido y presupuesto, y se actualiza inmediatamente después de cada llamada.
- [ ] Al superar el presupuesto mensual, la barra pasa a estado de alerta y se avisa una sola vez; las llamadas siguen funcionando.
- [ ] MVC respetado: `text_diff.py` y `claude_usage_model.py` no importan PySide6; `spend_meter_view.py` no lee `config.json` ni calcula costos; la orquestación vive en los controllers.
- [ ] Cada paso del plan deja la app ejecutable con `python main.py` sin romper flujos existentes.
- [ ] `CLAUDE.md` queda actualizado: OCR en vivo ya no es exclusivo de Tesseract, y figuran los módulos y claves nuevos.

## Decisions

- **Sí:** cascada Tesseract → Claude. Saber si el texto cambió exige transcribir, y Tesseract local es el detector gratuito. El costo es CPU en cada poll con cambio visual; el beneficio es cero llamadas pagas redundantes.
- **Sí:** el filtro de texto actúa con cualquier motor, no solo con Claude. Con Tesseract elimina el parpadeo del resultado y de la traducción, y deja el mecanismo probado antes de que haya dinero en juego.
- **Sí:** umbral de similitud (`difflib.SequenceMatcher`, biblioteca estándar) en vez de igualdad exacta. Tesseract produce jitter entre capturas idénticas (una letra que baila); la comparación exacta lo trataría como cambio real y anularía el filtro. Se descartó agregar una dependencia externa de comparación de texto.
- **Sí:** clave `engine` única compartida con OCR de imágenes (como venía de spec 13), más el interruptor `live_claude_enabled` con default apagado. Reutiliza el esquema existente y a la vez impide que elegir Claude para imágenes encienda por accidente el gasto continuo del polling.
- **Sí:** con Claude activo se muestra únicamente su texto, nunca el de Tesseract. Mostrar primero el texto de Tesseract daría feedback más rápido pero haría saltar el resultado entre dos calidades en cada cambio.
- **Sí:** una llamada bloqueada por cooldown queda pendiente y se despacha al vencer, en vez de descartarse. Descartarla podría perder un cambio de texto para siempre si los píxeles no vuelven a moverse.
- **Sí:** el cooldown es configurable (deslizador 1-120 s, default 10). El ritmo tolerable depende del contenido: subtítulos y chat en vivo no se parecen a un documento estático.
- **Sí:** ante un error de la API en el ciclo en vivo se detiene el polling. Un `QMessageBox` por tick sería inusable y, con la key inválida o la cuota agotada, seguir intentando cada 1500 ms no aporta nada.
- **Sí:** el medidor mide consumo propio calculado localmente desde `usage.input_tokens`/`output_tokens` por el pricing de Haiku 4.5. Es la única fuente exacta disponible sin credenciales adicionales.
- **Sí:** presupuesto mensual configurable como referencia, con reinicio automático al cambiar de mes calendario. Coincide con el modelo de facturación mensual de la API.
- **Sí:** el medidor avisa pero no bloquea. Decisión explícita del usuario: prefiere enterarse a que la app le corte una transcripción en curso.
- **Sí:** el medidor vive en una barra inferior global de `MainWindow`, no dentro de `LiveOcrView`. El gasto lo generan las dos vistas de OCR, y un único lugar donde mirarlo evita duplicar indicadores.
- **No:** consultar el saldo real de Anthropic. No existe endpoint público que lo devuelva; `cost_report` informa gasto consumido y exige una credencial de administración de la organización, y los headers `anthropic-ratelimit-*` miden cuota de tasa por minuto, no dinero.
- **No:** mostrar cuota de tasa restante como sustituto del crédito. Responde otra pregunta y se prestaría a leerse como saldo.
- **No:** contador propio en `LiveOcrView`. Absorbido por la barra inferior.
- **No:** exponer el intervalo de polling en Configuración. Queda fijo en `POLL_INTERVAL_MS`; el cooldown ya es la palanca que gobierna el gasto.

## Identified risks

| Riesgo | Mitigación |
|---|---|
| Correr Tesseract en cada poll con cambio visual consume CPU de forma continua, incluso cuando ninguna llamada a Claude se dispara. | Es el precio de no llamar a la API sin necesidad, y es exactamente lo que ya ocurre hoy. Quien necesite bajarlo puede subir la sensibilidad al cambio de imagen para que el diff de píxeles descarte más capturas antes de llegar a Tesseract. |
| Tesseract como detector puede reportar "sin cambio" en un texto que sí cambió pero que él lee mal (fuente decorativa, bajo contraste), y entonces Claude nunca se entera del cambio. | El umbral de similitud es configurable: bajarlo hace el filtro más permisivo. Además el filtro de confianza de la spec 15 ya descarta lecturas de baja calidad que agregarían ruido a la comparación. |
| El costo calculado localmente puede divergir del facturado por Anthropic si cambia el pricing de Haiku 4.5. | Las tarifas son constantes con nombre en `claude_usage_model.py` y un comentario que las marca como valor cacheado; corregirlas es cambiar dos números. La barra informa consumo propio estimado, no un estado de cuenta. |
| El medidor no ve el gasto hecho con la misma API key desde otras aplicaciones, así que puede subestimar el consumo real de la cuenta. | Queda declarado en el alcance y el rótulo de la barra habla del consumo de esta aplicación. El estado de cuenta real se consulta en la consola de Anthropic. |
| La barra inferior roba ~28 px de alto al área de contenido, y la ventana tiene tamaño fijo (`setFixedSize`, hoy 1200x600). | La barra solo se muestra con motor Claude, y las vistas usan layouts elásticos. Si alguna quedara apretada, se ajusta la altura fija de la ventana en el paso 7 antes de darlo por cerrado. |
| Cambiar la firma de `transcribe_image_claude` rompe `OcrController` si se actualiza solo uno de los dos archivos. | Ambos cambios ocurren en el mismo paso (6), y su prueba manual exige transcribir una imagen con Claude antes de avanzar. |
| El polling con Claude puede acumular gasto rápido si el contenido cambia de verdad todo el tiempo (subtítulos, chat en vivo). | Es lo que acotan el cooldown configurable y el interruptor de opt-in apagado por defecto, y lo que hace visible el medidor. El corte duro quedó explícitamente fuera de alcance por decisión del usuario. |
