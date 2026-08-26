# Plugins de OCR-Py

Esta carpeta es donde se instalan plugins de terceros: motores de OCR,
traductores o preprocesadores que la aplicación descubre al arrancar, sin
tocar su código.

## `plugins/` vs `plugins_core/`

- **`plugins_core/`** contiene los tres plugins esenciales de la aplicación
  (Tesseract, Claude Haiku, Argos Translate). Se distribuyen junto con la
  app y se actualizan cuando la app se actualiza; la aplicación nunca ofrece
  borrarlos. **No copie ni modifique nada ahí**: un plugin de terceros con
  el mismo nombre de carpeta que uno esencial se descarta automáticamente
  con error, así que tampoco sirve como atajo para "reemplazar" un
  esencial.
- **`plugins/`** (esta carpeta) es para sus propios plugins. Cada
  subcarpeta es un plugin independiente.

## Cómo se descubre un plugin

Al arrancar, la aplicación escanea cada subcarpeta de `plugins/`, lee su
`plugin.json`, importa su `__init__.py` y valida que exponga las funciones
que declara. Los cambios en `plugins/` **no se detectan en caliente**: hace
falta reiniciar la aplicación para que un plugin nuevo, editado o eliminado
se refleje en los selectores de Configuración.

Si algo falla al cargar un plugin (manifiesto inválido, `import` roto,
falta una función declarada), ese plugin queda descartado con un error
interno y el resto de la aplicación arranca normal: no aparece en los
selectores, pero tampoco impide usar los demás motores.

## Estructura de una carpeta de plugin

```
plugins/
  mi-plugin/
    plugin.json
    __init__.py
```

El nombre de la carpeta debe coincidir exactamente con el `id` declarado en
`plugin.json`.

## `plugin.json`

```json
{
  "id": "mi-plugin",
  "name": "Mi Plugin",
  "version": "1.0.0",
  "api_version": 1,
  "provides": ["ocr"],
  "description": "Descripción breve y opcional."
}
```

- **`id`** (obligatorio): debe ser igual al nombre de la carpeta. Es el
  valor que queda guardado en `engine` o `translation_engine` dentro de
  `config.json` cuando se selecciona este plugin.
- **`name`** (obligatorio): nombre visible en los selectores de
  Configuración.
- **`version`** (obligatorio): texto libre, solo informativo por ahora.
- **`api_version`** (obligatorio): debe ser `1`. Un valor distinto hace que
  el plugin no se importe.
- **`provides`** (obligatorio): lista no vacía con una o más de `"ocr"`,
  `"translation"`, `"preprocessing"`, `"export"` (esta última se acepta en
  el manifiesto pero todavía no se ejecuta).
- **`description`** (opcional): texto libre.

## Contrato de cada capacidad

En `__init__.py`, según lo que declare en `provides`, exponga la función
correspondiente a nivel de módulo:

```python
# capacidad "ocr"
def transcribe(image, language_code, settings, context) -> str: ...

# capacidad "translation"
def translate(text, source_lang, target_lang, settings, context) -> str: ...

# capacidad "preprocessing"
def preprocess(image, settings) -> list[tuple[str, Image.Image]]: ...
```

- **`image`**: `PIL.Image.Image` ya cargada en memoria. Su plugin nunca
  recibe una ruta de archivo.
- **`language_code`**: `"spa"`, `"eng"` o `"spa+eng"`. **`source_lang`** /
  **`target_lang`**: `"spa"` o `"eng"`.
- **`settings`**: diccionario con los ajustes propios de su plugin (ver
  más abajo); `{}` si no tiene nada configurado.
- **`context`**: instancia de `PluginContext` (ver más abajo).
- **`preprocess`** devuelve una lista de `(nombre, imagen)`.

Si declara una capacidad en `provides` sin la función correspondiente, el
plugin queda con error y no se indexa.

## `PluginContext`

Es la única superficie que la aplicación le presta a un plugin: no hace
falta importar nada de `model/`, `view/` ni `controller/` del proyecto.

- **`context.plugin_id`**: id de su propio plugin.
- **`context.preprocess(image) -> list[tuple[str, Image.Image]]`**:
  devuelve las variantes nativas de preprocesamiento de la aplicación,
  seguidas de las que aporten otros plugins con capacidad `preprocessing`
  activos. Un motor de OCR puede ignorarlo y usar `image` directamente
  (así lo hace, por ejemplo, el plugin de Claude).

## Ajustes en `config.json`

Los ajustes de cada plugin viven en `config.json`, bajo su propio `id`:

```json
{
  "plugins": {
    "mi-plugin": {
      "enabled": true,
      "settings": { "cualquier_clave": "cualquier_valor" }
    }
  }
}
```

Por ahora `settings` se edita a mano directamente en `config.json` (una
spec futura va a agregar campos en Configuración para esto). Lo que ponga
ahí llega tal cual al parámetro `settings` de su función.

## Ejemplo mínimo: un plugin de OCR que devuelve un texto fijo

`plugins/eco/plugin.json`:

```json
{
  "id": "eco",
  "name": "Eco (ejemplo)",
  "version": "1.0.0",
  "api_version": 1,
  "provides": ["ocr"],
  "description": "Plugin de ejemplo: siempre devuelve el mismo texto."
}
```

`plugins/eco/__init__.py`:

```python
def transcribe(image, language_code, settings, context):
    return "Hola desde el plugin eco"
```

Copie esta carpeta dentro de `plugins/`, reinicie la aplicación y "Eco
(ejemplo)" va a aparecer en el selector de motor OCR de Configuración.

## Import perezoso para dependencias pesadas

La aplicación importa el módulo de cada plugin al arrancar. Si su plugin
depende de una biblioteca pesada de importar (un SDK, un modelo de
machine learning), impórtela **dentro de la función**, no al principio del
archivo: un import pesado a nivel de módulo suma directamente al tiempo de
arranque de la aplicación, aunque su plugin nunca llegue a usarse.

## Ejecución en segundo plano

`transcribe`, `translate` y `preprocess` corren en un hilo de trabajo del
`QThreadPool` de la aplicación, no en el hilo principal de la interfaz. No
llame a nada de PySide6 (widgets, diálogos) desde estas funciones.

Si su plugin hace una llamada de red, agregue un timeout explícito: la
aplicación no tiene forma de cancelar una llamada colgada, y eso deja la
transcripción o traducción en curso indefinidamente.

## Manejo de errores

Si su plugin lanza una excepción, la aplicación la muestra en un mensaje
que nombra su plugin (formato: `El plugin «Nombre» falló: <detalle>`), sin
cerrarse ni cortar el ciclo de OCR en vivo.

## Aviso de seguridad

Un plugin es código Python de terceros que corre **con los mismos permisos
que la aplicación, en el mismo proceso**: no hay sandbox ni aislamiento de
ningún tipo. Copie en `plugins/` únicamente código en el que confíe, y
revise el `__init__.py` antes de instalar un plugin cuyo origen no conozca.
