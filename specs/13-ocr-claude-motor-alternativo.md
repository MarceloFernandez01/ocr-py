# Spec 13: OCR con Claude — motor OCR alternativo vía API de Anthropic

**Estado:** Implementado
**Dependencias:** `specs/01-mvp-ocr-tesseract-tkinter.md`, `specs/07-menu-configuracion-sidebar.md`, `specs/08-ocr-en-vivo.md` (gancho existente: clave única `engine` en `config.json`, compartida hoy con OCR en vivo, y combobox deshabilitado en `SettingsView`)
**Fecha:** 2026-07-18

**Objetivo:** Permitir transcribir imágenes con Claude Haiku 4.5 (vía SDK oficial `anthropic`) como motor OCR alternativo a Tesseract en la vista de OCR de imágenes, seleccionable desde Configuración, con la API key del usuario guardada de forma segura en el keyring del sistema operativo; OCR en vivo sigue usando Tesseract exclusivamente por ahora.

## Alcance

**Dentro del alcance:**

- Nuevo módulo `model/claude_ocr_model.py`: transcripción de imágenes vía Claude Haiku 4.5 (SDK oficial `anthropic`), con import perezoso del SDK (solo se importa si el motor Claude está seleccionado).
- Envío de la imagen completa a la API (sin tiling ni preprocesamiento propio de Tesseract), redimensionando solo si excede los límites de tamaño de la API de Anthropic.
- Instrucción de idioma en el prompt según la selección existente (Español/Inglés/Ambos), igual que hoy Tesseract usa `spa`/`eng`/`spa+eng`.
- Habilitar el combobox de motor OCR en `SettingsView` (hoy deshabilitado) con las opciones "Tesseract" y "Claude Haiku".
- Texto informativo permanente (no modal) en `SettingsView`, junto al combobox, indicando que Claude Haiku es un servicio pago de Anthropic, con el costo estimado por imagen.
- Flujo de carga de API key: al seleccionar "Claude Haiku" sin key guardada, se bloquea la selección y se pide la key vía diálogo; se guarda en el keyring del sistema (nueva dependencia `keyring`) bajo un servicio/usuario propio de la app.
- Campo de API key enmascarado en `SettingsView` una vez guardada, con botón "Cambiar" para reemplazarla.
- `OcrController` decide qué motor invocar (Tesseract o Claude) según la clave `engine` de `config.json`, incluyendo el flujo de recorte de región ya existente (spec 10), que aplica igual para ambos motores.
- Manejo de errores de la API de Claude (sin conexión, API key inválida, rate limit, cuota agotada) vía `QMessageBox`, sin fallback automático a Tesseract.
- Documento interno (no versionado en git) con el costo estimado por imagen según la pricing actual de Anthropic para Claude Haiku 4.5.
- Actualizar `requirements.txt` con `anthropic` y `keyring`, y el `CLAUDE.md` del proyecto (lista de dependencias externas aprobadas).

**Fuera del alcance:**

- OCR en vivo con Claude: `LiveOcrController` sigue usando Tesseract exclusivamente sin importar el valor de `engine`; se evaluará en una spec futura (costo de polling continuo contra una API paga).
- Selección de modelo Claude distinto a Haiku 4.5 (no hay configuración de modelo).
- Traducción del texto reconocido por Claude (ya cubierto por spec 11, independiente del motor OCR).
- Cifrado adicional en `config.json` para la API key: se usa el keyring del SO en vez de guardar la key (ni cifrada ni en texto plano) dentro de `config.json`.
- Reintentos automáticos ante fallos de red o rate limit de la API.
- Preprocesamiento (`image_preprocessing.py`) o tiling (`image_tiling.py`) para el flujo Claude: se envía la imagen completa sin pasar por esas variantes.

## Modelo de datos

**`config.json`** — la clave `engine` (ya existe, spec 08) pasa a tener un valor real además de `"tesseract"`:

```json
{
  "tesseract_path": "...",
  "theme": "dark",
  "engine": "tesseract"
}
```

- `engine`: `"tesseract"` (default) | `"claude"`. Sigue siendo la única clave, compartida con `LiveOcrController`, que la ignora (ver Alcance, fuera de alcance).
- La API key **no se guarda en `config.json`** — vive exclusivamente en el keyring del SO (ver abajo).

**Keyring (vía `keyring` lib)** — un único secreto:

- Servicio: `"ocr-py"`
- Usuario/clave: `"anthropic_api_key"`
- Valor: la API key de Anthropic en texto plano (el keyring la cifra a nivel de SO — ver sección de riesgos).

**`model/claude_ocr_model.py`** (nuevo módulo):

- `transcribe_image_claude(image: PIL.Image.Image, language_code: str, api_key: str) -> str`
  Envía la imagen completa a Claude Haiku 4.5 vía SDK `anthropic`, con un prompt de instrucción de idioma derivado de `language_code` (`"spa"` → instrucción en español, `"eng"` → inglés, `"spa+eng"` → ambos). Devuelve el texto transcripto. Redimensiona la imagen antes de enviarla solo si excede los límites de tamaño de la API.
- Excepciones propias de la librería `anthropic` (`AuthenticationError`, `APIConnectionError`, `RateLimitError`, etc.) se dejan propagar; `OcrController` las captura y las traduce a mensajes de `QMessageBox`.

**`view/settings_view.py`** — cambios sobre lo existente:

- `ENGINE_OPTIONS` pasa de `["Tesseract", "Claude Haiku (próximamente)"]` a `["Tesseract", "Claude Haiku"]`; `engine_combobox` deja de estar `setEnabled(False)`.
- Nuevo label informativo fijo (no modal) bajo el combobox de motor OCR, con el texto de aviso de costo.
- Nuevo campo de API key: `QLineEdit` en modo password + botón "Guardar"/"Cambiar", visible solo cuando el motor seleccionado es Claude. Estado enmascarado (`••••••••xxxx`) una vez guardada.
- Nuevas señales: `engine_changed(str)` (`"tesseract"` | `"claude"`) y `api_key_submitted(str)`.

**`controller/settings_controller.py`** — cambios sobre lo existente:

- Al recibir `engine_changed("claude")`: si no hay key en el keyring, dispara el flujo de bloqueo + diálogo de carga de key (ver Plan de implementación); si el usuario cancela, revierte el combobox a `"tesseract"`.
- Al recibir `api_key_submitted(key)`: guarda en el keyring vía `keyring.set_password("ocr-py", "anthropic_api_key", key)`, persiste `engine: "claude"` en `config.json`.

**`controller/ocr_controller.py`** — cambio sobre lo existente:

- Antes de transcribir, lee `engine` de `config.json`. Si es `"claude"`, obtiene la key vía `keyring.get_password("ocr-py", "anthropic_api_key")` y llama a `transcribe_image_claude`; si es `"tesseract"` (default), sigue el flujo actual sin cambios.

**Documento de costos** (no versionado, agregado a `.gitignore`): `costs/claude-haiku-pricing.md` con el desglose de pricing actual de Anthropic y el costo estimado por imagen.

## Implementation plan

Cada paso deja la app en un estado ejecutable con `python main.py`, sin regresiones sobre lo que ya funcionaba. Ningún paso deja código a medio conectar que rompa un flujo existente hasta el paso siguiente.

1. **Dependencias: `requirements.txt` y `CLAUDE.md`.** Agregar `anthropic` y `keyring` a `requirements.txt`. Actualizar la lista de dependencias externas aprobadas en `CLAUDE.md` (agregar `anthropic` y `keyring` junto a su justificación, análogo a como están documentadas `pytesseract`/`argostranslate`). Instalar ambas en el entorno.
   Prueba manual: `pip install -r requirements.txt` termina sin errores; `python main.py` sigue arrancando igual que antes (no se tocó ningún módulo de la app todavía).

2. **`model/claude_ocr_model.py` (nuevo módulo, aislado).** Crear el módulo con `transcribe_image_claude(image, language_code, api_key)`, import perezoso del SDK `anthropic` (el `import anthropic` va dentro de la función, no a nivel de módulo, siguiendo el mismo patrón que `translation_model.py` — ver memoria del proyecto). Nada de la app existente importa este módulo todavía, así que no puede romper nada.
   Prueba manual: `python -c "from model.claude_ocr_model import transcribe_image_claude; print('ok')"` imprime `ok` sin errores de import. `python main.py` sigue arrancando y funcionando igual que en el paso 1 (módulo nuevo, no conectado a nada).

3. **`view/settings_view.py`: habilitar UI de motor OCR y campo de API key (sin conectar lógica nueva todavía).** Cambiar `ENGINE_OPTIONS` a `["Tesseract", "Claude Haiku"]`, habilitar `engine_combobox`. Agregar el label informativo de costo, el campo de API key enmascarado + botón "Guardar"/"Cambiar" (oculto si el motor no es Claude), y las señales `engine_changed(str)` / `api_key_submitted(str)` — se emiten pero **nada las escucha todavía** (igual que hoy `theme_toggled` es la única señal conectada en `SettingsController`), por lo que no hay ningún comportamiento nuevo, solo la UI visible.
   Prueba manual: correr `python main.py`, ir a Configuración. Confirmar que el combo "Motor OCR" ahora deja elegir "Claude Haiku" y que al seleccionarlo aparece el campo de API key y el aviso de costo (sin que pase nada más al tipear o guardar — todavía no está conectado). Confirmar que el tema claro/oscuro y el resto de Configuración siguen funcionando exactamente igual que antes.

4. **`controller/settings_controller.py`: flujo completo de selección de motor y carga de API key.** Conectar `engine_changed` y `api_key_submitted`. Al elegir "Claude Haiku" sin key guardada (`keyring.get_password("ocr-py", "anthropic_api_key")` es `None`), bloquear la selección y disparar el diálogo de carga de key; si se cancela, revertir el combo a "Tesseract" (`set_engine_silent` análogo a `set_theme`). Al guardar la key: `keyring.set_password(...)`, persistir `engine: "claude"` en `config.json` (nueva función `save_engine()` en `config_model.py`, análoga a `save_theme()`), y actualizar el campo a estado enmascarado con botón "Cambiar". Esto ya deja el flujo de Configuración completo y funcional; el motor Claude aún no se usa al transcribir (paso 5).
   Prueba manual: seleccionar "Claude Haiku" sin key cargada → aparece el pedido de key; cancelar → el combo vuelve a "Tesseract". Repetir y cargar una key válida → el campo queda enmascarado con botón "Cambiar"; cerrar y reabrir la app → el combo sigue en "Claude Haiku" y el campo sigue enmascarado (persistencia en `config.json` + keyring). Confirmar con `keyring` (ej. Credential Manager de Windows) que la entrada `ocr-py`/`anthropic_api_key` existe.

5. **`controller/ocr_controller.py`: branch de motor al transcribir.** Antes de llamar a `transcribe_large_image`/`transcribe_cropped_image`, leer `engine` de `config.json`. Si es `"claude"`, obtener la key del keyring y llamar a `transcribe_image_claude` con la imagen (recortada si hay `_crop_box`, igual que hoy) y el idioma seleccionado; si es `"tesseract"` (default), sin cambios sobre el flujo actual.
   Prueba manual: con el motor en "Tesseract", transcribir una imagen y confirmar que el resultado es igual que antes de esta spec (sin regresión). Cambiar a "Claude Haiku" en Configuración, volver a OCR de imágenes, abrir una imagen con texto conocido, transcribir, y confirmar que el resultado proviene de Claude (texto coherente, tiempo de respuesta distinto al de Tesseract). Repetir con una región recortada (spec 10) y confirmar que solo transcribe el recorte.

6. **Manejo de errores de la API de Claude.** Capturar en `OcrController` las excepciones de `anthropic` (`AuthenticationError`, `APIConnectionError`, `RateLimitError`, y el resto vía `APIStatusError`) alrededor de la llamada a `transcribe_image_claude`, mostrando un `QMessageBox` con un mensaje específico por tipo de error (key inválida, sin conexión, límite de uso), sin fallback automático a Tesseract.
   Prueba manual: con el motor en "Claude Haiku", forzar cada caso de error por separado — desconectar la red y transcribir (esperar mensaje de "sin conexión"); guardar una key inválida vía "Cambiar" y transcribir (esperar mensaje de "API key inválida"). Confirmar que en ningún caso la app se cuelga ni transcribe con Tesseract sin avisar.

7. **Documento de costos (no versionado).** Crear `costs/claude-haiku-pricing.md` con el pricing actual de Claude Haiku 4.5 y el costo estimado por imagen (input + output tokens típicos de una transcripción OCR). Agregar `costs/` a `.gitignore`.
   Prueba manual: `git status` no muestra `costs/claude-haiku-pricing.md` como archivo para commitear.

8. **Verificación end-to-end.** Recorrido manual completo: alternar entre ambos motores varias veces desde Configuración; transcribir con recorte y sin recorte en ambos motores; confirmar que "OCR en vivo" (specs 08-09, 11) sigue usando Tesseract exclusivamente sin importar el motor seleccionado en Configuración (sin regresión); alternar tema claro/oscuro con el campo de API key visible; cerrar y reabrir la app para confirmar persistencia de `engine` y de la key en keyring. Revisión de imports rotos.
   Prueba: recorrido manual + revisión de imports rotos.

## Acceptance criteria

- [x] `requirements.txt` incluye `anthropic` y `keyring`; `CLAUDE.md` documenta ambas como dependencias externas aprobadas.
- [x] El combobox "Motor OCR" en Configuración deja elegir entre "Tesseract" y "Claude Haiku" (ya no está deshabilitado).
- [x] Al seleccionar "Claude Haiku" sin una API key guardada, la app bloquea la selección y pide la key antes de habilitar el motor; cancelar el diálogo revierte el combo a "Tesseract".
- [x] La API key ingresada se guarda en el keyring del sistema operativo (servicio `ocr-py`, usuario `anthropic_api_key`), nunca en texto plano ni cifrada dentro de `config.json`.
- [x] Una vez guardada, el campo de API key se muestra enmascarado con un botón "Cambiar" para reemplazarla.
- [x] Un texto informativo permanente (no modal) junto al combobox de motor OCR indica que Claude Haiku es un servicio pago, con el costo estimado por imagen.
- [x] Con el motor en "Tesseract", el flujo de OCR de imágenes (incluyendo tiling, preprocesamiento y recorte de región) funciona exactamente igual que antes de esta spec.
- [x] Con el motor en "Claude Haiku", transcribir una imagen (con o sin recorte de región) envía la imagen completa a la API de Anthropic y devuelve el texto reconocido, respetando el idioma seleccionado (Español/Inglés/Ambos) vía instrucción en el prompt.
- [x] Con el motor en "Claude Haiku", errores de la API (sin conexión, key inválida, rate limit, cuota agotada) se muestran vía `QMessageBox` con un mensaje específico, sin fallback automático a Tesseract.
- [x] `config.json` persiste `engine: "claude"` o `engine: "tesseract"` según la selección, sin perder `tesseract_path`/`theme` existentes.
- [x] "OCR en vivo" (specs 08-09, 11) sigue usando Tesseract exclusivamente sin importar el valor de `engine` en Configuración — sin regresión.
- [x] `costs/claude-haiku-pricing.md` existe con el pricing estimado, y `costs/` está en `.gitignore` (no se sube a git).
- [x] MVC respetado: `model/claude_ocr_model.py` no importa PySide6; `view/settings_view.py` no llama al SDK `anthropic` ni a `keyring` directamente; toda la orquestación vive en los controllers.
- [x] Cada paso del plan de implementación deja la app ejecutable con `python main.py` sin romper flujos existentes hasta el paso siguiente.

## Decisions

- **Sí:** OCR con Claude se implementa solo para OCR de imágenes en esta spec; OCR en vivo sigue exclusivamente con Tesseract. Motivo: el polling continuo de OCR en vivo contra una API paga tiene implicaciones de costo/rate-limit que ameritan evaluación y spec propia.
- **Sí:** modelo fijo `claude-haiku-4-5`, sin selector de modelo. Es el motor más económico apto para OCR simple; agregar selección de modelo queda fuera de alcance hasta que se pida explícitamente.
- **Sí:** SDK oficial `anthropic` vía llamadas síncronas simples (`client.messages.create`), sin streaming ni Tool Runner — no aplica para esta tarea (transcripción de una imagen, no un loop agentic).
- **Sí:** la API key se guarda en el keyring del sistema operativo (`keyring` lib) en vez de cifrada en `config.json`. Se descartó SHA-256 (hash de una sola vía, no permite recuperar la key en texto plano para llamar a la API) y cifrado Fernet con clave derivada de la máquina (menos seguro que delegar en el Credential Manager del SO, que es el estándar de la industria — Git Credential Manager, VS Code, AWS CLI usan el mismo mecanismo). Limitación aceptada: no protege contra un atacante con sesión activa como el usuario en el mismo equipo — eso está fuera del alcance de cualquier app de escritorio sin backend propio.
- **Sí:** sin preprocesamiento (`image_preprocessing.py`) ni tiling (`image_tiling.py`) para el flujo Claude — se envía la imagen completa. Esas técnicas existen para compensar limitaciones de Tesseract; Claude Haiku procesa la imagen completa vía vision API sin esas restricciones, así que reutilizar el pipeline sería complejidad innecesaria.
- **Sí:** idioma indicado vía instrucción en el prompt (según Español/Inglés/Ambos), igual que Tesseract usa `spa`/`eng`/`spa+eng`. Mantiene consistencia con el selector de idioma ya existente en la UI.
- **Sí:** errores de la API se muestran vía `QMessageBox` sin fallback automático a Tesseract. Consistente con el manejo de errores actual de `ocr_controller.py`; un fallback silencioso podría confundir al usuario sobre qué motor (y costo) se usó realmente.
- **Sí:** aviso de costo como texto fijo junto al combobox, no como diálogo modal antes de cada uso. Menos fricción que un diálogo recurrente; el usuario ya confirma explícitamente al cargar la API key la primera vez.
- **Sí:** clave única `engine` en `config.json`, compartida con OCR en vivo (que la ignora por ahora), en vez de separar en `ocr_engine`/`live_ocr_engine`. Evita un cambio de esquema no pedido; ya está establecida así desde spec 08.
- **Sí:** documento de costos en `costs/claude-haiku-pricing.md`, agregado a `.gitignore`, no versionado. Pedido explícito del usuario — información de pricing que puede cambiar y no forma parte del código.
- **Sí:** cada paso del plan de implementación deja la app en estado ejecutable, evitando el problema de la spec anterior (spec 12) donde un paso rompía el código hasta aplicar el siguiente. Los pasos se ordenan de "aislado y sin conectar" (módulo nuevo, UI sin señales conectadas) a "conectado e integrado", nunca al revés.
- **No:** reintentos automáticos ante fallos de red o rate limit. El SDK `anthropic` ya reintenta internamente errores transitorios (429, 5xx) por defecto; agregar lógica propia sería redundante para el alcance de este MVP.

## Identified risks

| Risk | Mitigation |
|---|---|
| El keyring del SO puede no estar disponible o fallar en algunos entornos (ej. Windows sin Credential Manager accesible, o backend de `keyring` no configurado). | `keyring.get_password`/`set_password` pueden lanzar excepción; se captura en `SettingsController` y se muestra un `QMessageBox` explicando que no se pudo guardar la key, sin dejar la app en un estado inconsistente (el combo revierte a "Tesseract"). |
| El costo por imagen estimado en `costs/claude-haiku-pricing.md` puede quedar desactualizado si Anthropic cambia el pricing de Claude Haiku 4.5. | El documento no se versiona ni se expone en la UI como valor exacto — el aviso en Configuración es una indicación general de que es un servicio pago, no un contador de costo en tiempo real; no depende de que el doc esté siempre actualizado para funcionar. |
| Imágenes muy grandes (fuera de los límites de tamaño de la API de Anthropic, ~5MB u 8000px) fallarían al enviarse completas sin tiling. | `transcribe_image_claude` redimensiona la imagen antes de enviarla solo si excede esos límites (ver Alcance), evitando el error de la API sin necesidad de reimplementar tiling. |
| Un usuario podría seleccionar "Claude Haiku" sin entender que genera costos reales por cada transcripción, ya que no hay confirmación modal por uso. | Se mitiga con el texto de aviso permanente junto al combobox (visible cada vez que se entra a Configuración con ese motor seleccionado) y con que cargar la key es un paso explícito y consciente del usuario. |
| El flujo de recorte (spec 10) asume coordenadas de imagen original; si `transcribe_image_claude` redimensiona la imagen internamente por límites de tamaño, un error de implementación podría desalinear qué región se envía. | El recorte se aplica sobre la imagen original **antes** de pasarla a `transcribe_image_claude` (mismo patrón que hoy usa `transcribe_cropped_image` con Tesseract); el redimensionado por límites de la API ocurre después, sobre la imagen ya recortada, sin afectar qué región se seleccionó. |
