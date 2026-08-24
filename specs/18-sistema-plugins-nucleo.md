# Spec 18 — Sistema de plugins: núcleo de carga y contratos

**Estado:** Aprobado
**Dependencias:** `specs/01-mvp-ocr-tesseract-tkinter.md` (motor Tesseract y `config.json`), `specs/03-preprocesamiento-ocr.md` (variantes y selección por confianza), `specs/11-traduccion-ocr-en-vivo.md` (traducción con argostranslate), `specs/13-ocr-claude-motor-alternativo.md` (selector de motor y API key en el keyring), `specs/16-filtro-cambio-texto-ocr-vivo.md` (Tesseract como detector de cambio de texto y medidor de gasto)
**Fecha:** 2026-08-21
**Objetivo:** Que un tercero pueda agregar un motor de OCR, un traductor o un preprocesador copiando una carpeta en `plugins/`, sin tocar el código de la aplicación.

## Contexto

Los tres motores actuales están cableados en los controladores. `OcrController.on_transcribe` decide con `engine == "claude"`, arma un `TranscriptionRunnable` con parámetros distintos por motor y llama a `transcribe_image_claude` o a `transcribe_large_image` según el caso. `LiveOcrController` repite la misma bifurcación con dos `QRunnable` separados. `SettingsView.engine_combobox` tiene dos opciones fijas y decide por índice (`"claude" if index == 1 else "tesseract"`). Agregar un cuarto motor hoy significa editar dos controladores, una vista y el mapa de índices.

Esta spec introduce una capa de indirección: un registro que descubre carpetas de plugin, valida su manifiesto, importa su módulo y las indexa por capacidad. Los controladores dejan de conocer motores y pasan a pedirle al registro "el proveedor de OCR con id X". Los tres motores nativos se convierten en plugins reales, pero **esenciales**: viven en su propia carpeta `plugins_core/`, la aplicación no ofrece borrarlos y solo se pueden desactivar cuando otro plugin activo cubre su capacidad. Así el contrato queda validado por tres casos reales sin que la app pueda quedarse sin motor de OCR ni sin traductor.

## Alcance

**Dentro del alcance:**

- Dos carpetas de plugins en la raíz del proyecto, junto a `config.json` (misma resolución de ruta que `model/config_model.py`, compatible con `sys.frozen`): `plugins_core/` para los esenciales (versionada en el repositorio) y `plugins/` para los de terceros.
- Manifiesto `plugin.json` por carpeta, con `id`, `name`, `version`, `api_version`, `provides` y `description`.
- `model/plugin_manifest.py` (nuevo): parseo y validación del manifiesto. Sin PySide6, sin importar plugins.
- `model/plugin_registry.py` (nuevo): descubrimiento, importación aislada, índice por capacidad, `PluginContext`, `PluginError`, regla de desactivación y recarga.
- Tres contratos implementados: `ocr`, `translation`, `preprocessing`. La capacidad `export` se acepta en el manifiesto pero no se despacha en esta spec.
- Conversión de los tres motores nativos en plugins esenciales: `plugins_core/tesseract/`, `plugins_core/claude/`, `plugins_core/argos/`, como envoltorios finos sobre el código de `model/`, que no se mueve ni se reescribe.
- Regla de desactivación de esenciales (`can_disable`) en el registro, y detección de instalación corrupta si falta o falla un esencial.
- Despacho por registro en `controller/ocr_controller.py` y `controller/live_ocr_controller.py`.
- `SettingsView.engine_combobox` alimentado desde el registro en vez de una lista fija; `translation_engine_combobox` (hoy un placeholder deshabilitado) alimentado igual y habilitado.
- Claves nuevas en `config.json`: `translation_engine` y `plugins`.
- `plugins/README.md` con el contrato documentado y el aviso de seguridad.
- Actualizar `CLAUDE.md`.

**Fuera del alcance (para la spec 19 y posteriores):**

- Vista "Plugins" en Configuración: lista de instalados, activar/desactivar desde la UI, mostrar los que fallaron y botón "Recargar plugins". Esta spec deja `reload_plugins()`, `can_disable()` y `enabled` leído de `config.json` listos en el registro; falta solo la superficie visual.
- Borrar o instalar plugins desde la aplicación. En esta spec ninguna acción de la app borra carpetas; los esenciales, además, quedan explícitamente marcados como no borrables para la spec 19.
- Campos de ajustes declarados en el manifiesto y renderizados en Configuración. En esta spec los ajustes existen y llegan al plugin, pero se editan a mano en `config.json`.
- Capacidad `export` y su UI (botón "Exportar" en `OcrView` / `LiveOcrView`).
- Instalación desde ZIP, descarga desde un catálogo remoto, o cualquier forma de instalación que no sea copiar una carpeta.
- Sandbox o restricción de permisos del código del plugin. Un plugin corre con los mismos permisos que la aplicación.
- Que un plugin aporte idiomas fuera de `spa` / `eng` / `spa+eng`. El selector de idioma sigue teniendo tres opciones fijas y el plugin recibe el mismo `language_code` que Tesseract.
- Que un plugin aporte vistas, botones, atajos o entradas de sidebar.
- Aislamiento por proceso o timeout de ejecución de un plugin colgado.
- Diálogo de confirmación antes de importar un plugin desconocido (opción descartada, ver Decisiones).

## Modelo de datos

### Manifiesto `plugin.json`, en `plugins_core/<carpeta>/` o `plugins/<carpeta>/`

```json
{
  "id": "tesseract",
  "name": "Tesseract OCR",
  "version": "1.0.0",
  "api_version": 1,
  "provides": ["ocr"],
  "description": "Motor OCR local vía pytesseract."
}
```

- `id` (obligatorio): identificador único, debe coincidir con el nombre de la carpeta. Es el valor que se guarda en `config.json` bajo `engine` / `translation_engine`.
- `name` (obligatorio): nombre visible en los selectores de Configuración.
- `version` (obligatorio): string libre, solo informativo en esta spec.
- `api_version` (obligatorio): entero. Debe ser igual a `PLUGIN_API_VERSION`; si no, el plugin no se importa y queda con error.
- `provides` (obligatorio): lista no vacía de capacidades. Valores válidos: `"ocr"`, `"translation"`, `"preprocessing"`, `"export"`. Un mismo plugin puede declarar varias.
- `description` (opcional): texto libre.

Ser esencial **no es un campo del manifiesto**: se deriva de la carpeta en la que el registro encontró el plugin. Un plugin de terceros no puede declararse esencial copiando una clave en su `plugin.json`.

### Contratos, en `<carpeta del plugin>/__init__.py`

```python
# capacidad "ocr"
def transcribe(image, language_code, settings, context) -> str: ...

# capacidad "translation"
def translate(text, source_lang, target_lang, settings, context) -> str: ...

# capacidad "preprocessing"
def preprocess(image, settings) -> list[tuple[str, Image.Image]]: ...
```

- `image`: `PIL.Image.Image` ya cargada en memoria. El plugin nunca recibe rutas de archivo.
- `language_code`: `"spa"`, `"eng"` o `"spa+eng"`. `source_lang` / `target_lang`: `"spa"` o `"eng"`.
- `settings`: diccionario del plugin leído de `config.json`; `{}` si no tiene nada configurado.
- `context`: instancia de `PluginContext` (abajo).
- `preprocess` devuelve una lista de `(nombre, imagen)`, mismo formato que `model/image_preprocessing.generate_variants`.
- Una capacidad declarada en `provides` sin su función correspondiente en el módulo es un error de carga: el plugin queda con error y no se indexa.

### `PluginContext`

Objeto que la aplicación le presta al plugin. Es la única superficie que un plugin necesita de la app: no importa nada de `model/`, `view/` ni `controller/`.

- `context.plugin_id: str` — id del plugin que está corriendo.
- `context.preprocess(image) -> list[tuple[str, Image.Image]]` — devuelve las variantes nativas de `model/image_preprocessing.generate_variants(image)` seguidas de las que aporten los plugins con capacidad `preprocessing` activos. Un motor puede ignorarlo y usar `image` directamente.

### `model/plugin_manifest.py` (nuevo, sin PySide6)

- `PLUGIN_API_VERSION = 1`
- `CAPABILITIES = ("ocr", "translation", "preprocessing", "export")`
- `CAPABILITY_FUNCTIONS = {"ocr": "transcribe", "translation": "translate", "preprocessing": "preprocess"}` — qué función debe exponer el módulo por cada capacidad despachable. `"export"` no aparece: se acepta en el manifiesto y no se valida en esta spec.
- `PluginManifest` (`dataclass`): `id`, `name`, `version`, `api_version`, `provides`, `description`.
- `parse_manifest(data: dict, folder_name: str) -> PluginManifest` — valida campos obligatorios, tipos, que `id == folder_name`, que `api_version == PLUGIN_API_VERSION` y que `provides` sea una lista no vacía de capacidades válidas. Lanza `ValueError` con un mensaje en español apto para mostrar al usuario.

### `model/plugin_registry.py` (nuevo, sin PySide6)

- `CORE_PLUGINS_DIR` y `USER_PLUGINS_DIR` — `plugins_core/` y `plugins/`, resueltas con la misma lógica de `_BASE_DIR` que `model/config_model.py`.
- `ESSENTIAL_PLUGIN_IDS = ("tesseract", "claude", "argos")` — los que deben existir en `plugins_core/`; si falta alguno o no carga, la app lo reporta como instalación corrupta.
- `SELECTABLE_CAPABILITIES = ("ocr", "translation")` — capacidades que tienen un proveedor seleccionado en `config.json`. Son las que gobierna la regla de desactivación.
- `LoadedPlugin` (`dataclass`): `id`, `name`, `version`, `provides`, `module`, `error` (`str | None`), `enabled` (`bool`), `essential` (`bool`, derivado de la carpeta de origen).
- `PluginError(Exception)` — envuelve una excepción de un plugin. Atributos `plugin_name` y `original`; `str()` devuelve `"El plugin «<nombre>» falló: <detalle>"`.
- `load_plugins() -> list[LoadedPlugin]` — escanea primero `plugins_core/` y después `plugins/`, cada una en orden alfabético; lee y valida cada `plugin.json`, importa el módulo con `importlib.util.spec_from_file_location` bajo el nombre `ocr_plugins.<id>` (sin depender de que las carpetas sean paquetes importables ni de `sys.path`) y verifica que existan las funciones de sus capacidades. Cualquier excepción se captura y queda en `error`; nunca propaga. Un plugin de `plugins/` con un `id` ya tomado por uno esencial se descarta con error, sin pisarlo. Cachea el resultado en una variable de módulo.
- `get_plugins() -> list[LoadedPlugin]` — devuelve el cache, cargando la primera vez.
- `reload_plugins() -> list[LoadedPlugin]` — descarta el cache y vuelve a escanear e importar. Definida en esta spec, la llama el botón de la spec 19.
- `list_providers(capability: str) -> list[LoadedPlugin]` — plugins sin error, habilitados y con esa capacidad.
- `get_provider(capability: str, plugin_id: str) -> LoadedPlugin | None`.
- `can_disable(plugin_id: str) -> tuple[bool, str]` — devuelve si el plugin se puede desactivar y, si no, el motivo en español listo para mostrar. Un plugin no esencial siempre se puede desactivar. Uno esencial solo si, para **cada** capacidad de `SELECTABLE_CAPABILITIES` que aporta, el proveedor seleccionado en `config.json` es otro plugin habilitado y sin error. Ejemplos: con `engine` en `"tesseract"`, desactivar `tesseract` se rechaza con `"Tesseract OCR es el motor de OCR seleccionado. Elija otro motor antes de desactivarlo."`; con `engine` en `"mi_motor"`, se permite. `claude` se puede desactivar salvo que sea el motor seleccionado; `argos`, salvo que sea el traductor seleccionado.
- `missing_essentials() -> list[str]` — ids de `ESSENTIAL_PLUGIN_IDS` que no cargaron. La app lo usa para avisar de una instalación corrupta en vez de dejar los selectores vacíos sin explicación.
- `run_ocr(plugin_id, image, language_code) -> str` y `run_translation(plugin_id, text, source_lang, target_lang) -> str` — resuelven el proveedor, arman el `PluginContext`, leen los `settings` de `config.json` y llaman a la función del plugin. Si el proveedor no existe o está en error, lanzan `PluginError`; si el plugin lanza, la excepción original se envuelve en `PluginError` conservando `original`.

La aplicación nunca borra carpetas de plugin: `plugins_core/` se distribuye con la app y su contenido solo cambia al actualizarla. La spec 19 no ofrecerá acción de borrado sobre esa carpeta, y su interruptor de activación consultará `can_disable` antes de escribir nada.

### `config.json` — claves nuevas

```json
{
  "engine": "tesseract",
  "translation_engine": "argos",
  "plugins": {
    "claude": { "enabled": true, "settings": {} }
  }
}
```

- `engine` ya existe y no cambia de significado: pasa a guardar el `id` del plugin de OCR activo. Los valores actuales (`"tesseract"`, `"claude"`) siguen siendo válidos porque son los ids de los plugins nativos: no hace falta migración.
- `translation_engine` (nuevo): id del plugin de traducción activo. Default `"argos"`.
- `plugins` (nuevo): diccionario por id con `enabled` (bool, default `true` si el id no figura) y `settings` (dict, default `{}`).
- Funciones nuevas en `model/config_model.py`: `save_translation_engine(str)`, `save_plugin_enabled(plugin_id, bool)`, `save_plugin_settings(plugin_id, dict)`, más los `setdefault` correspondientes.
- `KEYRING_SERVICE` / `KEYRING_USERNAME` se mueven de `controller/common.py` a `model/config_model.py`, para que `plugins/claude/` lea la API key sin importar nada de `controller/`. Se actualizan los imports en los tres controladores.

### Los tres plugins esenciales

- **`plugins_core/tesseract/`** — `transcribe` resuelve la ruta con `model/tesseract_locator.resolve_tesseract_path()`, parte la imagen con `model/image_tiling.prepare_tiles_from_image`, pide variantes a `context.preprocess(...)` y transcribe con `model/ocr_model.transcribe_image_variants`, leyendo `min_word_confidence` de `config.json`. Si no encuentra el ejecutable, lanza `RuntimeError` con un mensaje en español.
- **`plugins_core/claude/`** — `transcribe` toma la API key de `settings["api_key"]` o, si no está, del keyring; llama a `model/claude_ocr_model.transcribe_image_claude` y registra el gasto con `model/claude_usage_model.register_call` antes de devolver el texto. Ignora `context.preprocess` (Claude no tiene métrica de confianza para elegir entre variantes).
- **`plugins_core/argos/`** — `translate` delega en `model/translation_model.translate_text`.

Los tres usan exactamente el mismo contrato y el mismo manifiesto que un plugin de terceros: la única diferencia es la carpeta donde viven, que el registro traduce en `essential=True`. Eso les da tres propiedades: la aplicación no ofrece borrarlos, `can_disable` los protege mientras sean el proveedor seleccionado, y si alguno falta o no carga, `missing_essentials()` lo reporta como instalación corrupta con un mensaje que nombra el plugin ausente.

### Cambios en módulos existentes

- **`model/ocr_model.py`** — `transcribe_image_variants` suma un parámetro opcional `variants: list[tuple[str, Image.Image]] | None = None`; con `None` sigue llamando a `generate_variants` internamente (sin regresión). `transcribe_large_image` se elimina: queda sin llamadores y `transcribe_cropped_image` cubre el mismo caso, ya que `prepare_tiles(path)` es literalmente `prepare_tiles_from_image(Image.open(path))`.
- **`controller/ocr_controller.py`** — `TranscriptionRunnable` deja de conocer motores: recibe `plugin_id`, `image` y `language_code` y llama a `run_ocr`. `on_transcribe` conserva los dos chequeos previos interactivos por id (pedir la ruta de Tesseract, avisar si falta la API key de Anthropic) porque necesitan diálogos de la vista. La barra de gasto se refresca tras cada transcripción exitosa, sin condicionar por motor.
- **`controller/live_ocr_controller.py`** — los dos runnables (`LiveTranscriptionRunnable` y el de Claude) se unifican en uno que llama a `run_ocr(plugin_id, ...)`; el runnable de traducción llama a `run_translation(translation_engine, ...)`. El detector de cambio de texto de la spec 16 sigue siendo Tesseract, invocado explícitamente como `run_ocr("tesseract", ...)`; si ese plugin no está disponible, OCR en vivo cae al diff de píxeles de la spec 08 y avisa una vez. `live_claude_enabled` conserva su significado: con el motor `"claude"` y el interruptor apagado, OCR en vivo transcribe con el plugin `"tesseract"`.
- **`view/settings_view.py`** — `engine_combobox` y `translation_engine_combobox` se llenan con `(name, id)` desde `list_providers("ocr")` y `list_providers("translation")`; el de traducción deja de estar deshabilitado. `_on_engine_combobox_changed` emite el id del `itemData` en vez de decidir por índice, y `set_engine_silent` busca por id. `_update_engine_visibility` sigue mostrando los controles de Claude cuando el id es `"claude"`. Señal nueva `translation_engine_changed(str)`.
- **`controller/settings_controller.py`** — persiste el motor de traducción con `save_translation_engine`. La validación de API key sigue atada al id `"claude"`.

## Plan de implementación

1. **`model/plugin_manifest.py` (módulo aislado).** Constantes, `PluginManifest` y `parse_manifest`. Nada lo importa todavía.
   Prueba manual: `python -c "from model.plugin_manifest import parse_manifest; print(parse_manifest({'id':'x','name':'X','version':'1.0.0','api_version':1,'provides':['ocr']}, 'x'))"` imprime el dataclass; con `api_version: 2` o `provides: []` lanza `ValueError` con mensaje en español. `python main.py` arranca igual.

2. **`model/config_model.py`: claves nuevas y traslado de las constantes del keyring.** `setdefault` de `translation_engine` y `plugins`, los tres savers nuevos, y `KEYRING_SERVICE`/`KEYRING_USERNAME` movidas desde `controller/common.py` con los imports de los tres controladores actualizados.
   Prueba manual: borrar `config.json`, correr la app, confirmar que se regenera con las claves nuevas y que guardar/leer la API key desde Configuración sigue funcionando.

3. **`model/plugin_registry.py` con las dos carpetas vacías.** Descubrimiento en `plugins_core/` y `plugins/`, importación, índice, `PluginContext`, `PluginError`, `load_plugins`, `reload_plugins`, `list_providers`, `get_provider`, `can_disable`, `missing_essentials`, `run_ocr`, `run_translation`.
   Prueba manual: `python -c "from model.plugin_registry import get_plugins, list_providers, missing_essentials; print(get_plugins(), list_providers('ocr'), missing_essentials())"` devuelve listas vacías y los tres ids esenciales como faltantes, sin lanzar, con y sin las carpetas creadas. `python main.py` arranca igual.

4. **`plugins_core/tesseract/` + parámetro `variants` en `transcribe_image_variants`.** El envoltorio y el parámetro opcional. La aplicación todavía usa el camino viejo.
   Prueba manual: `python -c "from PIL import Image; from model.plugin_registry import run_ocr; print(run_ocr('tesseract', Image.open('ruta/a/imagen.png'), 'spa+eng'))"` devuelve el mismo texto que la app por el camino viejo. `list_providers('ocr')` ya devuelve un elemento y `can_disable('tesseract')` devuelve `False` con el motivo, porque es el motor seleccionado.

5. **`plugins_core/claude/` y `plugins_core/argos/`.** Los otros dos envoltorios, con `register_call` dentro del de Claude.
   Prueba manual: con API key cargada, `run_ocr('claude', imagen, 'spa')` devuelve texto y `claude_spend` en `config.json` sube en una llamada. `run_translation('argos', 'hola mundo', 'spa', 'eng')` devuelve la traducción. `missing_essentials()` ya devuelve lista vacía.

6. **`controller/ocr_controller.py`: despacho por registro.** `TranscriptionRunnable` unificado, `on_transcribe` resolviendo por id, eliminación de `transcribe_large_image`, refresco de la barra de gasto tras cada transcripción exitosa.
   Prueba manual: OCR de imágenes con Tesseract, con y sin recorte, con zoom aplicado, sobre una imagen grande que dispare tiling; luego con Claude, verificando que la barra de gasto sube. Provocar un error (API key inválida) y confirmar que el mensaje nombra el plugin y sigue siendo legible.

7. **`controller/live_ocr_controller.py`: despacho por registro.** Runnable unificado, traducción por registro, detector Tesseract explícito y fallback a diff de píxeles si no está disponible.
   Prueba manual: OCR en vivo con Tesseract; con Claude e interruptor apagado (debe transcribir con Tesseract); con Claude e interruptor encendido, confirmando el cooldown y que el panel solo muestra resultados de Claude. Traducir desde el botón de la vista y desde el del overlay. Renombrar `plugins_core/tesseract/` a mano y confirmar el aviso de instalación corrupta y la caída al diff de píxeles, sin que la app se cierre.

8. **`view/settings_view.py` + `controller/settings_controller.py`: selectores alimentados por el registro.** Ambos combos poblados desde `list_providers`, despacho por `itemData`, señal `translation_engine_changed` y su persistencia.
   Prueba manual: abrir Configuración, confirmar que el combo de OCR lista Tesseract y Claude por su `name` del manifiesto y que el de traducción ya no está deshabilitado; cambiar motor, cerrar y reabrir la app, confirmar que la selección persiste. Agregar una carpeta de plugin de prueba, reiniciar y confirmar que aparece en el combo.

9. **`plugins/README.md`.** Contrato de las tres capacidades con un ejemplo mínimo completo, formato del manifiesto, dónde van los ajustes en `config.json`, la diferencia entre `plugins/` y `plugins_core/` (y por qué no hay que tocar la segunda) y el aviso de que un plugin es código de terceros que corre con los permisos de la aplicación.
   Prueba: seguir el README desde cero para escribir un plugin de OCR trivial (que devuelva un texto fijo), copiarlo en `plugins/`, reiniciar y verlo funcionar en el selector; con ese plugin seleccionado, confirmar que `can_disable('tesseract')` pasa a `True`.

10. **Verificación end-to-end y `CLAUDE.md`.** Recorrido completo de las dos vistas con los tres plugins esenciales, un plugin de terceros y un plugin roto a propósito. Actualizar `CLAUDE.md`: módulos nuevos, las carpetas `plugins_core/` y `plugins/`, claves nuevas de `config.json`, cambios en controladores y vistas, y la spec en la lista.
    Prueba: recorrido manual + revisión de imports rotos.

## Criterios de aceptación

- [ ] Copiar una carpeta con `plugin.json` y una función `transcribe` en `plugins/`, reiniciar la app, y ver el motor en el selector de Configuración y poder transcribir con él.
- [ ] Los tres plugins esenciales viven en `plugins_core/` y quedan marcados con `essential=True`; ningún plugin de `plugins/` puede volverse esencial agregando claves a su `plugin.json`.
- [ ] `can_disable("tesseract")` devuelve `False` con un motivo en español mientras `engine` sea `"tesseract"`, y `True` cuando el motor seleccionado es otro plugin habilitado y sin error. Lo mismo para `argos` respecto de `translation_engine`.
- [ ] `can_disable` devuelve `True` para cualquier plugin no esencial, sin importar la selección.
- [ ] Con un id de `plugins_core/` faltante o fallado, `missing_essentials()` lo devuelve y la app avisa de instalación corrupta nombrando el plugin, en vez de mostrar un selector vacío sin explicación.
- [ ] Un plugin de `plugins/` que use un `id` ya tomado por un esencial se descarta con error y no reemplaza al esencial.
- [ ] Lo mismo con una función `translate` y el selector de motor de traducción.
- [ ] Un plugin con `provides: ["preprocessing"]` aporta variantes que aparecen en `context.preprocess(image)` y compiten por confianza en el plugin de Tesseract.
- [ ] Un plugin con `api_version` distinto de `1` no se importa, no aparece en los selectores y el resto de la app arranca normal.
- [ ] Un plugin con un `import` roto o un `plugin.json` inválido queda registrado con error, no aparece en los selectores y el resto de la app arranca normal.
- [ ] Un plugin que declara `"ocr"` pero no define `transcribe` queda con error y no se indexa.
- [ ] Una excepción lanzada por un plugin durante una transcripción se muestra en un mensaje que nombra el plugin, sin cerrar la aplicación ni cortar el ciclo de OCR en vivo.
- [ ] OCR de imágenes con Tesseract da el mismo resultado que antes de la spec, con recorte, con zoom y sobre una imagen que dispare tiling.
- [ ] OCR de imágenes con Claude da el mismo resultado que antes y suma exactamente una llamada al medidor de gasto.
- [ ] OCR en vivo con Claude y `live_claude_enabled` encendido sigue respetando el cooldown y el filtro de cambio de texto de la spec 16, y el panel nunca muestra resultados de Tesseract.
- [ ] OCR en vivo con Claude y `live_claude_enabled` apagado transcribe con el plugin `tesseract`.
- [ ] La traducción de OCR en vivo funciona igual que antes, ahora despachada por el registro.
- [ ] `engine` y `translation_engine` persisten en `config.json` y sobreviven a reiniciar la aplicación.
- [ ] Un `config.json` previo a esta spec (con `engine: "claude"` y sin las claves nuevas) sigue funcionando sin migración manual.
- [ ] Los ajustes escritos a mano en `plugins.<id>.settings` de `config.json` llegan al argumento `settings` de la función del plugin.
- [ ] `model/plugin_registry.py` y `model/plugin_manifest.py` no importan PySide6.
- [ ] Un plugin no necesita importar nada de `model/`, `view/` ni `controller/` para cumplir su contrato.
- [ ] `plugins/README.md` alcanza para escribir un plugin de OCR funcional sin leer el código de la aplicación.
- [ ] Cada paso del plan deja la app ejecutable con `python main.py` sin romper flujos existentes.
- [ ] `CLAUDE.md` queda actualizado con los módulos, la carpeta y las claves nuevas.

## Decisiones

- **Sí:** partir la feature en dos specs, con el núcleo primero. Cuatro contratos, el refactor de tres motores estables y una UI de gestión con ajustes dinámicos no entran en un plan de implementación revisable; la 18 deja la app funcionando y la 19 solo agrega superficie visual.
- **Sí:** carpeta suelta en `plugins/`, descubierta al arrancar. No requiere código de instalación, descompresión ni validación de rutas, y encaja con una app de escritorio autocontenida.
- **No:** paquetes pip con `entry_points`. Es el estándar de Python, pero obliga al usuario a manejar `pip` contra el intérprete correcto y rompe la distribución congelada con PyInstaller.
- **No:** instalación desde ZIP en esta spec. Es azúcar sobre "copiar una carpeta" y se puede sumar después sin cambiar el contrato.
- **Sí:** funciones a nivel de módulo como contrato. Es el estilo de todo el proyecto (`ocr_model`, `translation_model`, `claude_ocr_model` son funciones sueltas) y no obliga al plugin a importar nada de la app.
- **No:** clases base exportadas por la app. Acoplan el plugin a un import del proyecto y no compran validación que el registro no pueda hacer al importar.
- **Sí:** `provides` como lista. Un servicio que hace OCR y traducción se envuelve en una sola carpeta en vez de dos duplicadas.
- **Sí:** motores nativos convertidos en carpetas de plugin con el mismo contrato y el mismo manifiesto que uno de terceros. Valida el contrato con tres casos reales y evita la divergencia entre lo que la app puede hacer y lo que un plugin puede hacer.
- **Sí:** esos tres son **esenciales** y viven en `plugins_core/`, separada de `plugins/`. La aplicación no ofrece borrarlos y `can_disable` los protege mientras sean el proveedor seleccionado. Un sistema de plugins no debería poder dejar a la app sin motor de OCR ni sin traductor: la extensibilidad es para sumar opciones, no para desarmar la base.
- **No:** marcar los esenciales con una clave `"essential": true` en el manifiesto, dentro de la misma carpeta `plugins/`. Un plugin de terceros podría copiar la clave y auto-declararse esencial, y borrar `plugins/` de un tirón se llevaría los nativos puestos. Derivar la condición de la carpeta la vuelve infalsificable.
- **Sí:** desactivar un esencial solo cuando el proveedor seleccionado de su capacidad es otro plugin activo y sano. Es la regla más estricta de las tres evaluadas y la única que garantiza que la capacidad nunca queda huérfana; cambiar solo al proveedor que quede disponible sería una decisión tomada por la app a espaldas del usuario.
- **No:** permitir desactivar cualquier plugin siempre, avisando recién al usarlo. Deja la aplicación sin OCR con un click y el aviso llega tarde, cuando el usuario ya está intentando transcribir.
- **Sí:** esos plugins son envoltorios finos y el código de los motores no se mueve de `model/`. La lógica de las specs 03, 13, 15 y 16 queda intacta; mover `ocr_model.py`, `image_tiling.py` e `image_preprocessing.py` obligaría a reescribir imports en cuatro specs de código estable a cambio de nada funcional.
- **Sí:** `PluginContext` como argumento explícito en vez de que el plugin importe el registro. Deja por escrito qué le presta la app al plugin, permite versionar esa superficie y evita imports circulares entre el registro y los plugins que él mismo importa.
- **Sí:** las variantes de preprocesamiento se ofrecen a cualquier motor OCR vía `context.preprocess`. Cada autor decide si su motor sabe elegir entre variantes; Tesseract las usa con su métrica de confianza y Claude las ignora.
- **Sí:** aislar y avisar ante un plugin fallado, sin desactivarlo automáticamente. Un fallo transitorio de red no debería desactivar un motor y obligar a reactivarlo a mano; el estado "con error" ya evita que la app quede inusable.
- **No:** cortar la operación con un `QMessageBox` sin estado de error. Un solo plugin roto volvería inusable la aplicación hasta borrar la carpeta a mano.
- **Sí:** detección solo al arrancar, con `reload_plugins()` disponible para el botón de la spec 19. Recargar módulos ya importados de Python deja estado viejo vivo; el botón explícito acota ese riesgo a un acto deliberado, y una vigilancia automática de la carpeta lo dispararía a mitad de una transcripción en vivo.
- **Sí:** ajustes en `config.json` bajo `plugins.<id>.settings`, editados a mano hasta la spec 19. La estructura queda fijada ahora, así que la 19 solo pone campos encima sin cambiar ninguna firma.
- **No:** archivo de configuración propio dentro de la carpeta del plugin. Obligaría a la UI de la 19 a escribir dentro de carpetas de terceros y dispersaría la configuración en varios archivos.
- **Sí:** la firma incluye `settings` desde el primer día, aunque todavía no haya UI para llenarlo. Agregarlo después rompería el contrato de todos los plugins ya escritos.
- **Sí:** aviso de seguridad en `plugins/README.md`, sin diálogo de confirmación. Copiar una carpeta al directorio de la app ya es un acto deliberado; un modal al arranque castiga a quien instaló el plugin a propósito y no detiene a nadie.
- **No:** sandbox o restricción de permisos. No hay forma razonable de sandboxear código Python en el mismo proceso, y aislar por proceso es una spec entera en sí misma.
- **Sí:** eliminar `transcribe_large_image`. Queda sin llamadores y `prepare_tiles(path)` es exactamente `prepare_tiles_from_image(Image.open(path))`, así que `transcribe_cropped_image` cubre el mismo caso.
- **Sí:** conservar en `OcrController` los chequeos por id de la ruta de Tesseract y de la API key de Anthropic. Ambos necesitan un diálogo de la vista antes de transcribir, y generalizarlos requiere los prerrequisitos declarados en el manifiesto, que son de la spec 19.
- **No:** que un plugin aporte idiomas nuevos. El selector de tres opciones fijas es una restricción del proyecto desde la spec 01 y levantarla es una spec propia.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Los tres motores pasan a depender de que su carpeta exista en `plugins_core/`: borrarla a mano por fuera de la aplicación deja la app sin OCR, sin traducción y sin el detector de cambio de texto de la spec 16. | La app nunca borra esa carpeta y la spec 19 no ofrecerá la acción; `can_disable` impide desactivar un esencial sin reemplazo. Si aun así falta, `missing_essentials()` lo reporta como instalación corrupta nombrando el plugin, y el detector caído degrada OCR en vivo al diff de píxeles de la spec 08 en vez de cortarlo. |
| Con PyInstaller (`sys.frozen`), `plugins_core/` y `plugins/` deben quedar junto al ejecutable como archivos sueltos; empaquetadas dentro del binario, `spec_from_file_location` no las encuentra y la app arranca sin motores. | Ambas rutas se resuelven con la misma lógica de `_BASE_DIR` que ya usa `config.json`, que vive junto al ejecutable. Se verifica en el paso 10. |
| Actualizar la aplicación podría pisar plugins de usuario si ambas carpetas se mezclaran. | No se mezclan: la actualización reemplaza `plugins_core/`, que es contenido de la app, y no toca `plugins/`, que es del usuario. |
| Un plugin puede colgar el `QThreadPool` con una llamada de red sin timeout y dejar la transcripción en "Procesando..." para siempre. | Fuera del alcance resolverlo (requiere timeout o aislamiento por proceso). El contador de segundos en vivo hace visible el cuelgue y el `README` recomienda timeout explícito en cualquier llamada de red. |
| Importar plugins al arrancar suma tiempo de arranque proporcional a lo que cada plugin importe a nivel de módulo. | El `README` documenta el patrón de import perezoso que ya usan `translation_model.py` y `claude_ocr_model.py`, y los tres plugins nativos lo respetan como ejemplo. |
| Unificar los dos runnables de `LiveOcrController` toca el camino más delicado del proyecto (cooldown, cola de la captura más reciente, filtro de texto de la spec 16). | El paso 7 está aislado y su prueba manual recorre las tres combinaciones de motor e interruptor; el paso anterior deja `run_ocr` ya probado desde OCR de imágenes. |
| Dos plugins con el mismo `id` en carpetas distintas. | Imposible por construcción: `parse_manifest` exige `id == folder_name` y el sistema de archivos no admite dos carpetas iguales. |

## Continuación: qué queda para la spec 19

Esta lista es el insumo de la spec siguiente, acordado en la ronda de preguntas de la spec 18. No es un plan de implementación: cada punto se define en su propia spec, redactada con `/spec` cuando la 18 esté implementada.

- **Vista "Plugins" en Configuración.** Lista de plugins encontrados con su `name`, `version` y `description` del manifiesto, sus capacidades y su estado (activo / deshabilitado / con error). Los que quedaron con error muestran el mensaje que ya guarda `LoadedPlugin.error`.
- **Activar y desactivar desde la UI.** Interruptor por plugin que consulta `can_disable(id)` y, si devuelve `True`, escribe `plugins.<id>.enabled` con `save_plugin_enabled`; si devuelve `False`, muestra el motivo que ya trae la función. Los esenciales se marcan visualmente como tales y no ofrecen acción de borrado.
- **Aviso de instalación corrupta.** Superficie visual para lo que `missing_essentials()` ya detecta en la spec 18, con la indicación de reinstalar la aplicación.
- **Botón "Recargar plugins".** Llama a `reload_plugins()` (ya existe tras la spec 18) y repuebla los dos combos de motor sin reiniciar la aplicación. Requiere decidir el comportamiento si se recarga con una transcripción en curso.
- **Campos de ajustes declarados en el manifiesto.** Clave `settings` nueva en `plugin.json` describiendo los campos (nombre, tipo, etiqueta, default) para que Configuración los renderice y los persista en `plugins.<id>.settings` con `save_plugin_settings`. Esto sube `PLUGIN_API_VERSION` a `2`, con la regla de compatibilidad a definir en esa spec.
- **API key por plugin en el keyring del SO.** Un campo declarado como tipo `api_key` se guarda enmascarado en el keyring en vez de en `config.json`, generalizando lo que hoy hace el plugin `claude`.
- **Prerrequisitos interactivos declarados.** Generalizar los dos chequeos por id que la spec 18 deja cableados en `OcrController` (pedir la ruta de Tesseract, avisar si falta la API key), de forma que un plugin de terceros pueda declarar un prerrequisito y obtener el mismo diálogo previo.
- **Capacidad `export` y su UI.** Implementar el despacho de la capacidad que la spec 18 acepta en el manifiesto pero no ejecuta, más el botón "Exportar" en `OcrView` y `LiveOcrView` que despliega los plugins de exportación disponibles.

## Qué **no** está en esta spec

- Vista "Plugins" en Configuración y botón "Recargar plugins" (spec 19).
- Campos de ajustes declarados en el manifiesto y renderizados en la UI (spec 19).
- Capacidad de exportación y su botón (spec 19).
- Instalación desde ZIP o catálogo remoto de plugins.
- Sandbox, timeout o aislamiento por proceso del código de un plugin.
- Idiomas aportados por plugins.
- Plugins que aporten vistas, botones o atajos.
