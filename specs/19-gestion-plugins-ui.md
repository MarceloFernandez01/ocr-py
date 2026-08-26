# Spec 19 — Sistema de plugins: gestión y ajustes desde la UI

**Estado:** Aprobado
**Dependencias:** `specs/18-sistema-plugins-nucleo.md` (registro, manifiesto, contratos, plugins esenciales, `plugins_core/`)
**Fecha:** 2026-08-25
**Objetivo:** Agregar una vista "Plugins" en el sidebar para ver, activar/desactivar, configurar y recargar los plugins instalados, generalizando en el manifiesto sus ajustes (incluidos los campos obligatorios que hoy resuelven a mano Tesseract y Claude) en vez de los dos chequeos hardcodeados por id.

## Contexto

Spec 18 dejó el registro funcional (`load_plugins`, `list_providers`, `can_disable`, `missing_essentials`, `reload_plugins`) pero sin ninguna superficie visual: no hay forma de ver qué plugins se cargaron, activarlos o desactivarlos, saber si alguno falló, ni recargar tras copiar uno nuevo sin reiniciar la app. Además, `OcrController.on_transcribe` conserva dos chequeos hardcodeados por id (pedir la ruta de Tesseract, avisar si falta la API key de Anthropic) que spec 18 dejó así explícitamente "porque generalizarlos requiere los prerrequisitos... de la spec 19" (`specs/18-sistema-plugins-nucleo.md`, sección Decisiones).

Esta spec cierra ambos frentes con una sola idea: cada campo de ajuste declarado en el manifiesto puede marcarse `required`. Un prerrequisito no es un concepto nuevo, es un ajuste obligatorio — la ruta de Tesseract y la API key de Claude ya son exactamente eso. Con esto, el manifiesto gana un esquema `settings` que la vista "Plugins" renderiza genéricamente y que los controladores consultan antes de transcribir, sin conocer ids de motores concretos.

## Alcance

**Dentro del alcance:**

- Botón nuevo `plugins_button` en `view/sidebar_view.py` (ícono `"🧩"`, 48×48 px, mismo estilo que `settings_button`), ubicado junto al engranaje en la parte inferior del sidebar, dentro del mismo grupo de exclusividad (`_exclusive_buttons`). Señal nueva `plugins_selected`.
- Vista nueva `view/plugins_view.py` (`PluginsView`), independiente de `SettingsView`, agregada como cuarto widget del `QStackedWidget` de `MainWindow`.
- Controlador nuevo `controller/plugins_controller.py` (`PluginsController`), que conecta `PluginsView` con `model/plugin_registry.py`.
- Lista de plugins encontrados (esenciales y de terceros): nombre, versión, descripción, capacidades (`provides`) y estado (Activo / Deshabilitado / Con error, mostrando `LoadedPlugin.error` cuando aplica).
- Badge "Esencial" en los tres plugins nativos; sin interruptor de desactivar visible para ellos (ya protegidos por `can_disable`, no aporta mostrar un control que casi siempre va a rechazar la acción).
- Interruptor de activar/desactivar para plugins no esenciales, que persiste al instante vía el registro (sin botón "Guardar").
- Banner persistente en `PluginsView` cuando `missing_essentials()` no está vacío, visible mientras el problema exista, nombrando los ids esenciales faltantes.
- Botón "Recargar plugins": deshabilitado mientras `OcrController.state.transcription_in_progress` sea `True` o `LiveOcrController` no esté en estado `"Detenido"`. Al presionar: `reload_plugins()`, refresco de la lista propia y repoblado de `engine_combobox`/`translation_engine_combobox` en `SettingsView`.
- Acordeón inline por plugin (expandir/colapsar) con sus campos de ajuste declarados en el manifiesto, tipos `text`, `number`, `boolean`, `api_key`. Persisten al cambiar el valor (sin botón "Guardar" explícito), igual que el resto de `SettingsView` hoy.
- Extensión del manifiesto `plugin.json`: campo opcional `settings` (lista de campos), cada uno con `key`, `label`, `type`, `required` (default `false`), `default` (opcional).
- `PLUGIN_API_VERSION` sube de `1` a `2`. Los tres manifiestos esenciales se actualizan a `api_version: 2` y declaran sus campos: `tesseract` (`tesseract_path`, `text`, `required`), `claude` (`api_key`, `api_key`, `required`), `argos` (sin campos).
- `model/plugin_registry.py`: `resolve_setting_value`, `save_setting_value`, `missing_required_settings`, `set_enabled` (activa/desactiva sin reimportar módulos).
- Migración automática al arrancar: `tesseract_path` (hoy clave top-level de `config.json`) pasa a `plugins.tesseract.settings.tesseract_path`; la API key de Anthropic guardada bajo el username fijo `anthropic_api_key` del keyring pasa al esquema por plugin (`claude:api_key`).
- `controller/ocr_controller.py` y `controller/live_ocr_controller.py`: los dos chequeos hardcodeados por id se reemplazan por `missing_required_settings(plugin_id)`, con un diálogo genérico (`QInputDialog`) por campo faltante — texto normal para `text`, oculto para `api_key`.
- `main.py`: `OcrController` se guarda como `window.ocr_controller` (en vez de una variable local) para que `PluginsController` pueda consultar si hay una transcripción de imagen en curso.
- `view/metro_style.py`: selectores nuevos para el badge, el banner, las filas de la lista y el acordeón, en ambos temas.
- Actualizar `CLAUDE.md`.

**Fuera del alcance (para specs futuras):**

- Tipo de campo `select` (lista de opciones fijas). Ningún plugin esencial lo necesita hoy; se agrega cuando exista un caso real.
- Selector de archivo (`QFileDialog`) dentro del acordeón para campos de ruta. El campo `tesseract_path` es tipo `text` genérico (se pega la ruta a mano o se resuelve por el diálogo existente al transcribir); un tipo `path` con selector nativo queda para una spec futura si hace falta.
- Que desactivar un plugin no esencial que es el proveedor actualmente seleccionado (`engine`/`translation_engine`) cambie automáticamente la selección a otro proveedor. Queda como riesgo documentado, no resuelto en esta spec.
- Instalar o borrar plugins desde la UI (copiar/eliminar carpetas). Sigue siendo una acción manual del usuario sobre el sistema de archivos.
- Reordenar o buscar/filtrar la lista de plugins.
- Capacidad `export` y su UI.
- Sandbox, timeout o aislamiento por proceso del código de un plugin.
- Que un plugin declare prerrequisitos que no sean del tipo `text`, `number`, `boolean` o `api_key`.

## Modelo de datos

### Manifiesto `plugin.json` — campo `settings` nuevo

```json
{
  "id": "tesseract",
  "name": "Tesseract OCR",
  "version": "1.0.0",
  "api_version": 2,
  "provides": ["ocr"],
  "description": "Motor OCR local vía pytesseract.",
  "settings": [
    {
      "key": "tesseract_path",
      "label": "Ruta del ejecutable de Tesseract",
      "type": "text",
      "required": true,
      "default": ""
    }
  ]
}
```

```json
{
  "id": "claude",
  "settings": [
    {
      "key": "api_key",
      "label": "API key de Anthropic",
      "type": "api_key",
      "required": true,
      "default": ""
    }
  ]
}
```

`argos` no declara `settings` (lista vacía por default): `translate_text` no necesita ningún ajuste ni credencial.

- `key` (obligatorio): identificador del campo, único dentro del plugin. Es la clave bajo `plugins.<id>.settings` en `config.json` (salvo tipo `api_key`, que va al keyring).
- `label` (obligatorio): texto mostrado junto al campo en el acordeón.
- `type` (obligatorio): uno de `SETTING_FIELD_TYPES = ("text", "number", "boolean", "api_key")`.
- `required` (opcional, default `false`): si es `true`, un valor vacío bloquea usar el plugin y dispara el diálogo antes de transcribir.
- `default` (opcional): valor inicial si el usuario no guardó nada todavía.

### `model/plugin_manifest.py` — cambios

- `PLUGIN_API_VERSION` sube de `1` a `2`.
- `SETTING_FIELD_TYPES = ("text", "number", "boolean", "api_key")`.
- `SettingField` (`dataclass`): `key: str`, `label: str`, `type: str`, `required: bool = False`, `default: object = None`.
- `PluginManifest` suma el campo `settings: list[SettingField]` (default `[]`).
- `parse_manifest` valida: `settings` es una lista (o ausente, default `[]`); cada elemento tiene `key`/`label`/`type` obligatorios, `type` dentro de `SETTING_FIELD_TYPES`, `key` único dentro del mismo manifiesto. `required`/`default` son opcionales. Cualquier violación lanza `ValueError` con mensaje en español, igual que las validaciones existentes.

### `model/plugin_registry.py` — funciones nuevas

- `resolve_setting_value(plugin_id: str, field_key: str) -> object` — busca el `SettingField` por `key` en el manifiesto del plugin. Si `type == "api_key"`, lee del keyring bajo `model.config_model.plugin_keyring_username(plugin_id, field_key)`; si no hay valor y `plugin_id == "claude"` y `field_key == "api_key"`, revisa el username legacy `KEYRING_USERNAME` (`"anthropic_api_key"`), y si lo encuentra lo migra (guarda en la ubicación nueva, borra la vieja) antes de devolverlo. Para cualquier otro tipo, lee `config["plugins"][plugin_id]["settings"].get(field_key, field.default)`.
- `save_setting_value(plugin_id: str, field_key: str, value: object) -> None` — mismo despacho: `api_key` va al keyring bajo el username nuevo; el resto llama a `model.config_model.save_plugin_setting_field(plugin_id, field_key, value)`.
- `missing_required_settings(plugin_id: str) -> list[SettingField]` — de los `SettingField` del plugin con `required=True`, devuelve los que `resolve_setting_value` resuelve a un valor "vacío" (`None`, `""`).
- `set_enabled(plugin_id: str, enabled: bool) -> None` — persiste con `model.config_model.save_plugin_enabled` y actualiza `enabled` en el `LoadedPlugin` cacheado, para que `list_providers`/la vista reflejen el cambio sin `reload_plugins()`.
- `run_ocr`/`run_translation` (ya existentes en spec 18) pasan a construir el `settings` que reciben los plugins resolviendo cada campo declarado con `resolve_setting_value`, en vez de leer directo `config["plugins"][plugin_id]["settings"]`. Esto hace que `plugins_core/claude/__init__.py` deje de necesitar su propio fallback a `keyring.get_password(...)`: `settings["api_key"]` ya llega resuelto.

### `model/config_model.py` — cambios

- `plugin_keyring_username(plugin_id: str, field_key: str) -> str` — devuelve `f"{plugin_id}:{field_key}"`. `KEYRING_SERVICE` no cambia; `KEYRING_USERNAME` se conserva solo como referencia para la migración de la API key legacy de Claude.
- `save_plugin_setting_field(plugin_id: str, key: str, value: object) -> None` — actualiza una sola clave dentro de `plugins.<id>.settings`, preservando el resto de campos y de `enabled` (mismo patrón de merge que ya usa `save_plugin_enabled`).
- `save_tesseract_path` se elimina: su único llamador (`controller/common.py: prompt_tesseract_path`) pasa a llamar `model.plugin_registry.save_setting_value("tesseract", "tesseract_path", path)`.
- `load_config()`: si existe la clave top-level legacy `tesseract_path`, su valor se mueve a `plugins.tesseract.settings.tesseract_path` (creando la entrada si no existe) y se borra la clave top-level; el archivo se reescribe solo si la migración ocurrió.

### `model/tesseract_locator.py` — cambio

- `resolve_tesseract_path()` deja de leer `config.get("tesseract_path")` y pasa a leer `config.get("plugins", {}).get("tesseract", {}).get("settings", {}).get("tesseract_path")`. Como `load_config()` ya migró la clave legacy antes de devolver el diccionario, esto no requiere ningún caso especial adicional.

### `controller/ocr_controller.py` / `controller/live_ocr_controller.py` — cambio

- El bloque `if engine == "claude": ... elif engine == "tesseract": ...` de `on_transcribe` (y su equivalente en `live_ocr_controller.py`) se reemplaza por: `missing = missing_required_settings(engine)`; si no está vacía, por cada `SettingField` en `missing` se pide el valor con `QInputDialog.getText(view, field.label, field.label, echo=QLineEdit.Password if field.type == "api_key" else QLineEdit.Normal)`, y si el usuario completa el diálogo se llama a `save_setting_value(engine, field.key, valor)`; si cancela cualquiera, se aborta la transcripción sin arrancarla.

### `view/plugins_view.py` (nuevo)

- `PluginsView(QWidget)` — sin lógica de negocio, solo presentación y señales.
- `set_plugins(loaded_plugins: list[LoadedPlugin]) -> None` — repuebla la lista completa (filas con nombre, versión, descripción, capacidades, estado, badge esencial cuando aplica, interruptor cuando no es esencial, acordeón de campos de `settings_schema`).
- `set_corrupt_banner(missing_ids: list[str]) -> None` — muestra u oculta el banner persistente.
- `set_reload_enabled(enabled: bool) -> None`.
- Señales: `reload_requested`, `plugin_enabled_toggled(str, bool)`, `plugin_setting_changed(str, str, object)` (`plugin_id`, `field_key`, valor nuevo).

### `controller/plugins_controller.py` (nuevo)

- `PluginsController(view: PluginsView, main_window: "MainWindow")`.
- Al mostrarse la vista (señal `plugins_selected` de `sidebar_view`) o tras recargar: llama `get_plugins()`/`missing_essentials()` y puebla la vista.
- `reload_requested` → si `main_window.ocr_controller.state.transcription_in_progress` o `main_window.live_ocr_controller._status != "Detenido"`, ignora (el botón ya debería estar deshabilitado); si no, `reload_plugins()`, repuebla `PluginsView` y llama a un método nuevo de `SettingsView` que repuebla ambos combos desde `list_providers`.
- `plugin_enabled_toggled` → `set_enabled(plugin_id, enabled)`, repuebla la fila correspondiente.
- `plugin_setting_changed` → `save_setting_value(plugin_id, field_key, valor)`.

### `main.py` — cambio

- `controller = OcrController(window.ocr_view, window)` pasa a `window.ocr_controller = OcrController(window.ocr_view, window)`, para que `PluginsController` pueda leer `window.ocr_controller.state.transcription_in_progress`.

## Plan de implementación

1. **`model/plugin_manifest.py`: esquema `settings` y bump a `api_version: 2`.** `SETTING_FIELD_TYPES`, `SettingField`, campo `settings` en `PluginManifest`, validación en `parse_manifest`. Actualizar los tres manifiestos de `plugins_core/` con `api_version: 2` y sus campos.
   Prueba manual: `python -c "from model.plugin_manifest import parse_manifest; print(parse_manifest({'id':'x','name':'X','version':'1.0.0','api_version':2,'provides':['ocr'],'settings':[{'key':'k','label':'K','type':'text','required':True}]}, 'x'))"` imprime el manifiesto con su `SettingField`; con `type: 'bad'` lanza `ValueError`. `python main.py` arranca igual (los tres esenciales siguen cargando con `api_version: 2`).

2. **`model/config_model.py` + `model/tesseract_locator.py`: migración de `tesseract_path` y `save_plugin_setting_field`.** Migración en `load_config()`, función nueva, `plugin_keyring_username`, eliminación de `save_tesseract_path`, actualización de `controller/common.py`.
   Prueba manual: con un `config.json` que tenga `tesseract_path` top-level (de una versión anterior), arrancar la app y confirmar que la clave se movió a `plugins.tesseract.settings.tesseract_path` y que OCR con Tesseract sigue funcionando.

3. **`model/plugin_registry.py`: resolución/guardado de ajustes y migración de la API key legacy.** `resolve_setting_value`, `save_setting_value`, `missing_required_settings`, `set_enabled`; `run_ocr`/`run_translation` arman `settings` resolviendo cada campo declarado; `plugins_core/claude/__init__.py` deja de tener su propio fallback a keyring.
   Prueba manual: con una API key guardada bajo el esquema viejo (`anthropic_api_key`), `python -c "from model.plugin_registry import resolve_setting_value; print(resolve_setting_value('claude', 'api_key'))"` la devuelve y confirma (con `keyring` en otra terminal, o releyendo) que quedó migrada al username nuevo `claude:api_key`. `run_ocr('claude', imagen, 'spa')` sigue funcionando igual que antes de esta spec.

4. **`controller/ocr_controller.py` + `controller/live_ocr_controller.py`: prerrequisitos genéricos.** Reemplazo de los dos chequeos hardcodeados por `missing_required_settings` + `QInputDialog` genérico.
   Prueba manual: borrar la API key del keyring, elegir motor Claude y transcribir; confirmar que aparece un diálogo pidiendo "API key de Anthropic" con eco oculto, y que completar y aceptar permite transcribir. Vaciar `plugins.tesseract.settings.tesseract_path`, elegir Tesseract y transcribir; confirmar que aparece un diálogo de texto pidiendo la ruta. Cancelar cualquiera de los dos diálogos y confirmar que no arranca la transcripción.

5. **`main.py` + `view/sidebar_view.py` + `view/main_window.py`: entrada del sidebar y cuarta vista vacía.** `window.ocr_controller`, botón `"🧩"` junto al engranaje, señal `plugins_selected`, `PluginsView` placeholder agregada al stack.
   Prueba manual: aparece el nuevo botón en el sidebar, cambiar a esa sección muestra un panel vacío, los otros tres botones y vistas siguen funcionando igual.

6. **`view/plugins_view.py`: lista, badge, banner, botón recargar (sin ajustes inline todavía).** `set_plugins`, `set_corrupt_banner`, `set_reload_enabled`, señal `reload_requested`.
   Prueba manual: abrir "Plugins", ver los tres esenciales con badge "Esencial" y sin interruptor, banner oculto (instalación sana). Renombrar temporalmente `plugins_core/tesseract/` a mano, reiniciar, confirmar que el banner aparece nombrando `tesseract`; restaurar el nombre.

7. **`view/plugins_view.py`: acordeón de ajustes e interruptor de activar/desactivar.** Campos `text`/`number`/`boolean`/`api_key` por plugin, guardado al cambiar; interruptor visible solo en no esenciales.
   Prueba manual: cambiar la ruta de Tesseract desde el acordeón y confirmar que persiste (revisar `config.json`) y que OCR sigue funcionando; guardar una API key desde el acordeón de Claude y confirmar que ya no hace falta ir a Configuración para transcribir con Claude.

8. **`controller/plugins_controller.py`: conectar todo.** `reload_requested` (con el botón deshabilitado durante una transcripción), `plugin_enabled_toggled` → `set_enabled`, `plugin_setting_changed` → `save_setting_value`, repoblado de los combos de `SettingsView` tras recargar.
   Prueba manual: copiar un plugin de prueba en `plugins/`, presionar "Recargar plugins" y confirmar que aparece en la lista y en el combo de motor de Configuración sin reiniciar la app. Iniciar una transcripción larga (imagen grande) y confirmar que el botón "Recargar plugins" queda deshabilitado mientras dura. Desactivar un plugin no esencial y confirmar que su interruptor queda apagado de inmediato.

9. **`view/metro_style.py`: estilos.** Selectores para el badge, el banner, las filas de la lista, el acordeón y el interruptor, en tema claro y oscuro.
   Prueba manual: recorrer la vista "Plugins" alternando tema claro/oscuro, confirmar legibilidad del banner y el badge en ambos.

10. **Verificación end-to-end y `CLAUDE.md`.** Recorrido completo: los tres esenciales, un plugin de terceros de prueba y un plugin roto a propósito (import inválido); activar/desactivar, editar ajustes, recargar, provocar el banner de instalación corrupta y los dos diálogos de prerrequisito. Actualizar `CLAUDE.md` con los módulos y vistas nuevos, el campo `settings` del manifiesto, `PLUGIN_API_VERSION = 2` y las funciones nuevas del registro.
    Prueba: recorrido manual + revisión de imports rotos.

## Criterios de aceptación

- [ ] La vista "Plugins" se abre desde un botón nuevo en el sidebar, junto al engranaje, y queda resaltada como las demás mientras está activa.
- [ ] La lista muestra los tres plugins esenciales con badge "Esencial", sin interruptor de desactivar, y cualquier plugin de `plugins/` con su interruptor activo/inactivo.
- [ ] Un plugin con `LoadedPlugin.error` no `None` muestra ese mensaje como su estado, sin romper el resto de la lista.
- [ ] Con algún id de `ESSENTIAL_PLUGIN_IDS` faltante o fallado, el banner de instalación corrupta aparece y nombra el id; desaparece si el problema se resuelve y se recarga.
- [ ] "Recargar plugins" está deshabilitado mientras haya una transcripción de imagen o de OCR en vivo en curso, y habilitado el resto del tiempo.
- [ ] Presionar "Recargar plugins" hace aparecer un plugin nuevo copiado en `plugins/` tanto en la lista como en los combos de motor de `SettingsView`, sin reiniciar la app.
- [ ] Desactivar un plugin no esencial actualiza su interruptor de inmediato, sin necesitar "Recargar plugins".
- [ ] El acordeón de cada plugin muestra sus campos declarados en `settings` con el tipo correcto (`text`, `number`, `boolean`, `api_key` enmascarado).
- [ ] Cambiar un campo del acordeón persiste el valor (en `config.json` o en el keyring según el tipo) sin necesitar un botón "Guardar".
- [ ] Un `config.json` con `tesseract_path` en su ubicación vieja (top-level) se migra a `plugins.tesseract.settings.tesseract_path` al arrancar, sin intervención manual.
- [ ] Una API key guardada bajo el username viejo del keyring (`anthropic_api_key`) se migra al esquema nuevo (`claude:api_key`) la primera vez que se resuelve, sin pedirla de nuevo al usuario.
- [ ] Transcribir con Tesseract sin `tesseract_path` configurado dispara un diálogo pidiendo la ruta; completarlo permite transcribir, cancelarlo aborta sin transcribir.
- [ ] Transcribir con Claude sin API key guardada dispara un diálogo con el campo oculto pidiéndola; completarlo permite transcribir, cancelarlo aborta sin transcribir.
- [ ] Un plugin con `api_version` distinto de `2` no se importa y no aparece en la lista de "Plugins" ni en los combos de motor, igual que describía spec 18 para `api_version` distinto de `1`.
- [ ] `model/plugin_manifest.py` y `model/plugin_registry.py` siguen sin importar PySide6.
- [ ] Cada paso del plan deja la app ejecutable con `python main.py` sin romper flujos existentes.
- [ ] `CLAUDE.md` queda actualizado con los módulos, vistas y el campo `settings` del manifiesto.

## Decisiones

- **Sí:** unificar "ajustes" y "prerrequisitos" en un solo esquema `settings` con la marca `required`. Evita mantener dos listas paralelas en el manifiesto para resolver el mismo problema (un valor que el plugin necesita antes de funcionar).
- **No:** mantener `prerequisites` como lista separada de `settings`. Habría dos formas de declarar casi lo mismo en el manifiesto, con reglas de validación duplicadas.
- **Sí:** cuatro tipos de campo (`text`, `number`, `boolean`, `api_key`), sin `select`. Cubren los tres plugins esenciales; `select` se agrega el día que un plugin real lo necesite.
- **Sí:** `tesseract_path` como campo `text` genérico, sin un tipo `path` con selector de archivo nativo. Agregar un quinto tipo de campo solo para un caso (la ruta de Tesseract) no se justifica todavía; el diálogo de prerrequisito ya existente sigue ofreciendo el selector nativo cuando falta.
- **Sí:** vista "Plugins" como entrada nueva del sidebar, no como pestaña dentro de "Configuración". Es administración igual que "Configuración" pero con su propia superficie (lista + acordeones), y mezclarla dentro de `SettingsView` la sobrecargaría.
- **Sí:** ajustes renderizados inline en un acordeón, sin `QDialog` propio. Consistente con que toda la app es un único `MainWindow` que cambia de panel embebido, sin ventanas emergentes de contenido.
- **Sí:** guardar cada campo al cambiar su valor, sin botón "Guardar" explícito por plugin. Es el patrón ya establecido en el resto de `SettingsView` (tema, sliders, motor).
- **Sí:** plugins esenciales sin interruptor de desactivar visible, solo badge. `can_disable` casi siempre rechaza la acción para ellos; mostrar un control que casi nunca funciona es peor que no mostrarlo, y el motivo de rechazo ya no tiene dónde comunicarse sin un interruptor.
- **Sí:** "Recargar plugins" deshabilitado durante cualquier transcripción en curso (imagen o en vivo). Recargar módulos ya importados con una transcripción corriendo deja ambigüedad sobre qué versión del código la resolvió; deshabilitar el botón es más simple que sincronizar ambos.
- **Sí:** el botón de recarga también repuebla los combos de `SettingsView`. Si no lo hiciera, un plugin nuevo aparecería en la lista de "Plugins" pero seguiría invisible como opción de motor hasta reiniciar, lo que contradice el propósito del botón.
- **Sí:** bump de `PLUGIN_API_VERSION` a `2`, actualizando los tres manifiestos esenciales, rompiendo compatibilidad con plugins de terceros que declaren `api_version: 1`. El ecosistema de terceros recién nace (spec 18 se acaba de implementar); mantener dos versiones coexistiendo no tiene beneficio real todavía.
- **Sí:** migración automática de `tesseract_path` y de la API key legacy del keyring, sin pedirle nada al usuario. Ambos valores ya existen guardados; una migración silenciosa evita una fricción que no aporta nada.
- **Sí:** la migración de la API key legacy queda acotada explícitamente a `plugin_id == "claude"` y `field_key == "api_key"`, en vez de un fallback genérico a un username fijo para cualquier plugin con un campo `api_key`. Un fallback genérico migraría por error la API key de Claude hacia el primer plugin de terceros que declare un campo `api_key` propio y todavía no tenga valor guardado.
- **No:** que desactivar el proveedor actualmente seleccionado (`engine`/`translation_engine`) lo cambie automáticamente a otro. La app quedaría decidiendo por el usuario qué motor usar; queda documentado como riesgo, no resuelto.
- **Sí:** `window.ocr_controller` en vez de una variable local en `main.py`. Es el cambio mínimo necesario para que `PluginsController` pueda consultar si hay una transcripción de imagen en curso sin duplicar el estado en otro lugar.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Desactivar un plugin no esencial que es el proveedor actualmente seleccionado (`engine`/`translation_engine`) deja esa clave apuntando a un plugin deshabilitado. | Fuera de alcance resolverlo en esta spec (ver Decisiones). El usuario debe elegir otro motor en Configuración antes de desactivar el que está usando. |
| Bump de `PLUGIN_API_VERSION` a `2` deja inutilizable cualquier plugin de terceros ya escrito contra la versión `1` (los que existieran entre la spec 18 y esta). | El ecosistema de terceros recién nace; se documenta en `plugins/README.md` (actualización menor de esta spec) y el plugin queda con error visible en la lista, no falla en silencio. |
| La migración de la API key legacy corre en `resolve_setting_value`, en el primer acceso: si nunca se llama antes de que el usuario borre la key vieja a mano desde otra herramienta, la migración nunca ocurre. | Caso extremo poco probable (el keyring del SO no se edita a mano habitualmente); si ocurre, el usuario simplemente vuelve a pegar la API key una vez, como si fuera nueva. |
| El diálogo genérico de prerrequisito (`QInputDialog`) para `tesseract_path` pierde el selector de archivo nativo que ya existía (`QFileDialog.getOpenFileName`). | Aceptado como trade-off menor (ver Decisiones); el usuario pega la ruta a mano. Si resulta muy incómodo en la prueba manual del paso 4, se puede revisar antes de aprobar la spec. |

## Qué **no** está en esta spec

- Tipo de campo `select` y tipo `path` con selector de archivo nativo en el acordeón.
- Cambiar automáticamente `engine`/`translation_engine` al desactivar el proveedor seleccionado.
- Instalar o borrar plugins desde la UI.
- Reordenar, buscar o filtrar la lista de plugins.
- Capacidad `export` y su UI.
- Sandbox, timeout o aislamiento por proceso del código de un plugin.
