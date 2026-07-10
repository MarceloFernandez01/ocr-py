# SPEC 01 — MVP de aplicativo de escritorio OCR

> **Status:** Implementado
> **Depends on:** (ninguna)
> **Date:** 2026-07-09
> **Objective:** Construir una app de escritorio en Python (Tkinter + patrón MVC) que permita cargar una imagen en cualquier formato, elegir idioma (español, inglés o ambos) y transcribir su texto usando Tesseract OCR, mostrando la imagen y el texto reconocido en la misma ventana.

## Scope

**In:**

- Ventana de escritorio (Tkinter) con: botón "Abrir imagen", selector de idioma (Español / Inglés / Ambos), botón "Transcribir", vista previa de la imagen cargada y un bloque de texto de solo lectura con el resultado del OCR.
- Carga de imagen en cualquier formato soportado por Pillow (JPEG, PNG, BMP, TIFF, WEBP, GIF, etc.) mediante diálogo de selección de archivo.
- Transcripción del texto de la imagen usando Tesseract OCR (vía `pytesseract`), con el idioma configurado por el usuario (`spa`, `eng` o `spa+eng`), disparada explícitamente con el botón "Transcribir".
- Detección de Tesseract instalado: intento automático vía PATH del sistema.
- Si Tesseract no se encuentra en el PATH: diálogo para que el usuario indique manualmente la ruta al ejecutable (`tesseract.exe`), validando que el archivo exista.
- Persistencia de la ruta de Tesseract configurada manualmente en `config.json`, para no volver a pedirla en próximas ejecuciones (si el archivo sigue existiendo en esa ruta).
- Estructura de código respetando MVC: `model/` (lógica de OCR y config), `view/` (ventana y widgets Tkinter), `controller/` (conecta eventos de la vista con el modelo).
- Manejo de errores visibles en la UI: imagen inválida/corrupta, Tesseract no encontrado ni configurado, fallo de transcripción.

**Out of scope (para futuras specs):**

- Diseño visual pulido / estilo "metro" (por ahora la interfaz es puramente funcional, sin estética cuidada).
- OCR en vivo / captura de pantalla o "espacios" (transcripción en tiempo real de regiones de pantalla).
- Guardado del texto transcrito a archivo (por ahora solo se muestra en el bloque de texto de la app).
- Historial de transcripciones entre sesiones.
- Instalación automática de Tesseract (silenciosa o asistida) — el usuario debe instalarlo manualmente.
- Idiomas adicionales más allá de español/inglés/ambos.
- Cambio de framework de GUI (se deja abierta la posibilidad a futuro, pero no se diseña una capa de abstracción para eso ahora).
- Motor ICR (Intelligent Character Recognition) o pre-procesamiento de imagen (binarización, enderezado, reducción de ruido) para mejorar precisión en imágenes borrosas o con tipografía muy estilizada.

## Data model

### `config.json` (en la raíz del proyecto, junto a `main.py`)

```json
{
  "tesseract_path": "C:/Program Files/Tesseract-OCR/tesseract.exe"
}
```

- Se crea/actualiza solo cuando el usuario indica manualmente la ruta de Tesseract (no se encontró en el PATH).
- Si el archivo no existe, se asume que no hay ruta configurada y se intenta detectar por PATH.
- Si la ruta guardada ya no existe en disco (ej. se desinstaló o se movió Tesseract), se descarta y se vuelve a pedir al usuario.

### Mapeo de idioma (selector → código Tesseract)

```python
LANGUAGE_MAP = {
    "Español": "spa",
    "Inglés": "eng",
    "Ambos": "spa+eng",
}
```

### Estado en memoria de la app (no persistido, vive en el Controller/Model mientras la app está abierta)

```python
class AppState:
    image_path: str | None      # ruta de la imagen cargada actualmente
    selected_language: str      # una de las claves de LANGUAGE_MAP, default "Ambos"
    tesseract_ready: bool       # si se pudo resolver la ruta del ejecutable
```

## Implementation plan

1. **Scaffolding del proyecto.** Crear estructura `model/`, `view/`, `controller/` (con `__init__.py`), `requirements.txt` (`pytesseract`, `Pillow`) y `main.py` con una ventana Tkinter vacía que abre y cierra sin errores.
   Prueba manual: `python main.py` abre una ventana en blanco.

2. **Model — configuración.** Crear `model/config_model.py` con `load_config()` y `save_tesseract_path(path)`, leyendo/escribiendo `config.json`. Si el archivo no existe, `load_config()` devuelve `{}`.
   Prueba manual: llamar las funciones desde una consola Python y verificar que `config.json` se crea/lee correctamente.

3. **Model — localización de Tesseract.** Crear `model/tesseract_locator.py` con `resolve_tesseract_path()`: intenta `shutil.which("tesseract")`; si falla, revisa `config.json`; si la ruta guardada no existe en disco, la descarta. Devuelve la ruta o `None`.
   Prueba manual: probar con y sin Tesseract en el PATH.

4. **View — layout base.** Crear `view/main_view.py` con los widgets: botón "Abrir imagen", `Combobox` de idioma (`Español`, `Inglés`, `Ambos`, default `Ambos`), botón "Transcribir", área de vista previa de imagen (`Label` con `PhotoImage`), y `Text` de solo lectura para el resultado. Sin lógica de negocio, solo layout y setters/getters simples (`set_preview_image`, `set_result_text`, `get_selected_language`).
   Prueba manual: la ventana muestra todos los widgets correctamente distribuidos, con "Transcribir" deshabilitado hasta que haya una imagen cargada.

5. **Controller — carga de imagen y vista previa.** Crear `controller/ocr_controller.py`, conectar el botón "Abrir imagen" a `filedialog.askopenfilename` (sin restricción de extensión), abrir la imagen con Pillow, redimensionarla para que entre en el área de preview, mostrarla vía `view.set_preview_image`, y habilitar el botón "Transcribir".
   Prueba manual: cargar una imagen JPEG y una PNG, ambas se ven en la vista previa y "Transcribir" se habilita.

6. **Model — transcripción OCR.** Crear `model/ocr_model.py` con `transcribe(image_path, language_code, tesseract_path)`: configura `pytesseract.pytesseract.tesseract_cmd` si `tesseract_path` no es `None`, y llama `pytesseract.image_to_string`.
   Prueba manual: invocar `transcribe(...)` directamente desde consola con una imagen de prueba y verificar que devuelve texto reconocible.

7. **Controller — acción del botón "Transcribir".** Al presionar "Transcribir", el Controller toma la imagen cargada y el idioma seleccionado, llama a `resolve_tesseract_path()` + `transcribe(...)`, y vuelca el resultado en `view.set_result_text`. Cambiar el idioma no reprocesa automáticamente — hay que volver a presionar "Transcribir".
   Prueba manual: cargar imagen, elegir idioma, presionar "Transcribir" y ver el resultado; cambiar idioma y volver a presionar para confirmar que usa el nuevo idioma.

8. **Controller — manejo de Tesseract no encontrado.** Si al presionar "Transcribir" `resolve_tesseract_path()` devuelve `None`, mostrar un diálogo (`filedialog.askopenfilename` filtrado a ejecutables) pidiendo la ruta manual; validar que el archivo exista; guardarla con `save_tesseract_path`; reintentar la transcripción.
   Prueba manual: renombrar temporalmente el Tesseract del PATH y verificar que la app pide la ruta y luego la recuerda en la siguiente ejecución.

9. **Controller — manejo de errores de imagen/OCR.** Envolver la carga de imagen y la transcripción en manejo de excepciones, mostrando el error en la UI (ej. `messagebox.showerror`) sin crashear la app: imagen corrupta/no soportada, fallo de Tesseract al ejecutar.
   Prueba manual: intentar abrir un archivo que no es una imagen válida y verificar que se muestra un error controlado.

10. **Ensamblado final en `main.py`.** Instanciar Model, View y Controller, conectarlos, y dejar el `if __name__ == "__main__":` como único punto de entrada.
    Prueba manual: flujo completo de punta a punta — abrir la app, cargar imagen, elegir idioma, presionar "Transcribir" y ver texto transcrito.

## Acceptance criteria

- [x] La app abre una ventana Tkinter sin errores al ejecutar `python main.py`.
- [x] El botón "Abrir imagen" permite seleccionar un archivo de imagen en cualquier formato soportado por Pillow (JPEG, PNG, BMP, TIFF, WEBP, GIF, etc.).
- [x] Al cargar una imagen válida, se muestra su vista previa dentro de la ventana.
- [x] El botón "Transcribir" está deshabilitado hasta que haya una imagen cargada.
- [x] El selector de idioma ofrece exactamente tres opciones: "Español", "Inglés" y "Ambos", con "Ambos" como valor por defecto.
- [x] Al presionar "Transcribir" con idioma "Español", el texto reconocido usa el modelo `spa`.
- [x] Al presionar "Transcribir" con idioma "Inglés", el texto reconocido usa el modelo `eng`.
- [x] Al presionar "Transcribir" con idioma "Ambos", el texto reconocido usa el modelo combinado `spa+eng`.
- [x] El resultado de la transcripción se muestra en un bloque de texto de solo lectura dentro de la misma ventana.
- [x] Si Tesseract está instalado y en el PATH del sistema, la transcripción funciona sin pedir configuración adicional.
- [x] Si Tesseract no está en el PATH, la app pide al usuario la ruta del ejecutable mediante un diálogo de selección de archivo.
- [x] La ruta de Tesseract indicada manualmente se guarda en `config.json` y se reutiliza en la siguiente ejecución de la app, sin volver a pedirla (mientras el archivo siga existiendo en esa ruta).
- [x] Si se intenta cargar un archivo que no es una imagen válida, la app muestra un mensaje de error controlado sin cerrarse ni crashear.
- [x] Si la transcripción falla (ej. Tesseract no puede procesar la imagen), la app muestra un mensaje de error controlado sin cerrarse ni crashear.
- [x] El código está organizado siguiendo el patrón MVC: `model/`, `view/` y `controller/` con responsabilidades separadas (el Model no importa Tkinter, la View no llama a `pytesseract` directamente).

## Decisions

- **Sí:** Tesseract OCR vía `pytesseract` como motor de reconocimiento. Gratuito, potente para texto impreso multi-fuente, y mucho más liviano que alternativas basadas en deep learning.
- **No:** EasyOCR / PaddleOCR. Requieren PyTorch por debajo (cientos de MB–GB de dependencias), contradice la restricción de minimizar módulos externos.
- **Sí:** Tkinter como framework de GUI. Viene en la librería estándar de Python, sin dependencias adicionales, suficiente para un MVP funcional (se deja abierta la posibilidad de cambiarlo más adelante).
- **Sí:** Pillow (`PIL`) como segunda dependencia externa "estrictamente necesaria". Tkinter por sí solo no puede decodificar JPEG/BMP/TIFF/WEBP para la vista previa, y el requisito es soportar "cualquier formato de imagen".
- **No:** Instalación automática de Tesseract (silenciosa o asistida). Requeriría permisos de administrador, embeber instaladores binarios pesados, y lógica distinta por sistema operativo — demasiada complejidad para un MVP.
- **Sí:** El usuario instala Tesseract manualmente. La app detecta automáticamente por PATH del sistema (`shutil.which`); si no lo encuentra, pide la ruta manualmente vía diálogo de archivo.
- **Sí:** Persistir la ruta de Tesseract configurada manualmente en `config.json`. Evita pedirla en cada ejecución; si la ruta guardada deja de existir, se vuelve a pedir.
- **Sí:** Botón "Transcribir" explícito, separado de "Abrir imagen". Da control claro al usuario sobre cuándo se ejecuta el OCR (en vez de disparar automáticamente al cargar imagen o cambiar idioma).
- **Sí:** Selector de idioma con tres opciones fijas (`Español`, `Inglés`, `Ambos`), mapeadas a los códigos de Tesseract `spa`, `eng`, `spa+eng`. Idiomas adicionales quedan fuera de este MVP.
- **No:** Guardado del texto transcrito a archivo o historial entre sesiones. El resultado se muestra solo en el bloque de texto de la app mientras está abierta.
- **No:** Diseño visual pulido o estilo "metro". La interfaz de este MVP es puramente funcional.

## Risks

| Risk                                                                 | Mitigation                                                                                          |
| --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Usuario no tiene Tesseract instalado y no sabe cómo hacerlo           | Mensaje de error claro al fallar la detección, pidiendo instalar Tesseract-OCR manualmente.          |
| Ruta guardada en `config.json` queda obsoleta (Tesseract se reinstaló en otra ubicación o se desinstaló) | Se valida que el archivo exista antes de usarla; si no, se descarta y se vuelve a pedir.              |
| Imagen en formato no soportado o corrupta                             | Manejo de excepciones en la carga con Pillow; mensaje de error controlado, la app no crashea.        |
| Imagen borrosa o con tipografía muy estilizada reduce la precisión del OCR | Aceptado como limitación conocida de este MVP (Tesseract es un motor OCR, no ICR). Si se vuelve un problema recurrente, evaluar en una spec futura un motor con reconocimiento inteligente de caracteres (ICR) o pre-procesamiento de imagen (binarización, enderezado, etc.). |
| Rutas con espacios o caracteres especiales en Windows al invocar Tesseract | `pytesseract` maneja esto internamente vía `subprocess`; no requiere manejo adicional en esta spec.  |

## What is **not** in this spec

- Diseño visual pulido / estilo "metro" (interfaz puramente funcional por ahora).
- OCR en vivo / captura de pantalla o "espacios" (transcripción en tiempo real de regiones de pantalla).
- Guardado del texto transcrito a archivo o historial de transcripciones entre sesiones.
- Instalación automática de Tesseract (silenciosa o asistida) — el usuario debe instalarlo manualmente.
- Idiomas adicionales más allá de español/inglés/ambos.
- Cambio de framework de GUI (se deja abierta la posibilidad a futuro, pero no se diseña una capa de abstracción para eso ahora).
- Motor ICR (Intelligent Character Recognition) o pre-procesamiento de imagen (binarización, enderezado, reducción de ruido) para mejorar precisión en imágenes borrosas o con tipografía muy estilizada.

Cada uno de estos, si se implementa, va en su propia spec.
