# SPEC 04 — Migración a PySide6 con menú de inicio

> **Status:** Aprobado
> **Depends on:** `specs/03-preprocesamiento-ocr.md`
> **Date:** 2026-07-12
> **Objective:** Migrar la interfaz gráfica de Tkinter a PySide6, introduciendo una
> pantalla de inicio con menú de opciones (hoy solo OCR de imágenes) dentro de una
> única ventana de tamaño fijo (1200x900 / min 600x400), con tema oscuro fijo por
> default.

## Scope

**In:**

- **Nueva dependencia externa aprobada: `PySide6`.** Reemplaza a `tkinter` como toolkit
  de GUI. Se agrega a `requirements.txt`. `Pillow` se mantiene (decodificación de
  imágenes para preview), igual que `numpy`/`opencv-python` (preprocesamiento, sin
  cambios).
- **`main.py`** pasa a instanciar una `QApplication`, crear la `MainWindow` (PySide6) y
  correr `app.exec()` en vez del loop de Tkinter.
- **`view/main_window.py`** — `QMainWindow` con un `QStackedWidget` que aloja dos
  pantallas: `HomeView` y `OcrView`. Fija el tamaño default (1200x900) y el mínimo
  (600x400) de la ventana. Aplica el tema oscuro fijo a toda la app (paleta/QSS).
- **`view/home_view.py`** — pantalla de inicio con:
  - Botón "OCR de imágenes" (habilitado) que navega a `OcrView` dentro del mismo
    `QStackedWidget`.
  - Uno o más botones placeholder (ej. "OCR en vivo") **deshabilitados**, dejando el
    layout preparado para futuras opciones sin funcionalidad real.
- **`view/ocr_view.py`** — reemplaza a `view/main_view.py`: mismos widgets y
  responsabilidades que la `MainView` actual (botón abrir imagen, combobox de idioma,
  botón transcribir, preview, área de resultado, setters/getters), pero construidos con
  widgets de PySide6 (`QPushButton`, `QComboBox`, `QLabel`, `QTextEdit`, etc.). Suma un
  botón **"Volver"** que navega de vuelta a `HomeView` en el mismo `QStackedWidget`.
- **`controller/ocr_controller.py`** se mantiene con la misma responsabilidad (conectar
  eventos de la vista con el Model), migrado para conectarse a la nueva `OcrView` en vez
  de `MainView`. El threading interno pasa de `threading.Thread` + `view.after(...)`
  (polling) a `QThread` + señales (`pyqtSignal`/`Signal`) para actualizar el contador de
  segundos y el resultado final de forma thread-safe.
- **Diálogos**: `tkinter.filedialog`/`messagebox` se reemplazan 1:1 por
  `QFileDialog`/`QMessageBox` para abrir imagen, pedir ruta de Tesseract manualmente y
  mostrar errores (imagen inválida, Tesseract no encontrado, fallo de transcripción).
- **Tema oscuro**: se aplica de forma fija (paleta/QSS oscuro) a toda la aplicación desde
  `main.py` o `main_window.py` al arrancar.
- **`model/config_model.py`** se extiende con una clave nueva `"theme"` en `config.json`
  (default `"dark"` si no existe), leída al arrancar para aplicar el tema. No hay UI
  todavía para cambiarla (ver "Out of scope").
- El Model (`ocr_model.py`, `image_tiling.py`, `image_preprocessing.py`,
  `tesseract_locator.py`) **no cambia**: ya no importa Tkinter, sigue funcionando igual
  bajo PySide6 sin modificaciones (respeta MVC).

**Out of scope (para futuras specs):**

- Un menú/pantalla de "opciones" donde el usuario pueda cambiar el tema claro/oscuro
  desde la UI (toggle). Esta spec solo deja la clave `"theme"` en `config.json` y aplica
  el valor `"dark"` fijo; no hay control visual para cambiarlo.
- Tema claro o cualquier paleta alternativa: el QSS/paleta que se define en esta spec es
  únicamente la oscura.
- Nuevas opciones funcionales en el menú de inicio más allá de "OCR de imágenes" (ej.
  OCR en vivo, ICR): quedan como botones deshabilitados/placeholder sin lógica.
- Rediseño visual "pulido" o estilo "metro": se mantiene la filosofía de interfaz
  funcional del proyecto, ahora con PySide6 y tema oscuro, sin trabajo de diseño
  adicional.
- Empaquetado/distribución de la app (ej. PyInstaller) — sigue fuera de alcance como
  hasta ahora.
- Cambios de comportamiento funcional del OCR (tiling, preprocesamiento, selector de
  idioma): se migran tal cual están, sin modificar su lógica.

## Data model

### `config.json` (extendido)

Se agrega una clave nueva junto a la ya existente de la ruta de Tesseract:

```json
{
  "tesseract_path": "...",
  "theme": "dark"
}
```

- `"theme"` — string, valor fijo `"dark"` en esta spec (no hay forma de escribir otro
  valor desde la UI todavía). Si la clave no existe en un `config.json` preexistente, se
  asume `"dark"` por default.

### `model/config_model.py` (funciones nuevas/extendidas)

```python
def load_config() -> dict:
    """Ya existente. Se extiende el dict devuelto para incluir 'theme' (default 'dark'
    si la clave no está presente en el archivo)."""
```

No se agregan más funciones: no hace falta un `save_theme()` en esta spec porque no hay
UI que lo modifique; el valor default se escribe solo si `save_tesseract_path()` u otro
flujo ya reescribe el archivo completo (a confirmar en el paso de implementación
correspondiente).

### Vistas nuevas (`view/`)

No son estructuras de datos persistidas, pero introducen las clases:

```python
class MainWindow(QMainWindow):
    """Ventana única de la app. Contiene un QStackedWidget con HomeView y OcrView,
    fija tamaño default/mínimo y aplica el tema oscuro. No contiene lógica de negocio."""

class HomeView(QWidget):
    """Pantalla de inicio: botón 'OCR de imágenes' + placeholders deshabilitados para
    futuras opciones. Emite una señal al elegir una opción habilitada."""

class OcrView(QWidget):
    """Reemplaza a MainView (Tkinter): mismos widgets/responsabilidades para el flujo
    de OCR de imágenes, más un botón 'Volver'. No importa pytesseract directamente."""
```

## Implementation plan

1. **Dependencias.** Agregar `PySide6` a `requirements.txt`. Actualizar `CLAUDE.md` para
   reflejar el cambio de toolkit (Tkinter → PySide6) y la nueva estructura de `view/`.
   Prueba: `python -c "import PySide6"` sin error.
2. **Model — `config_model.py`.** Extender `load_config()` para incluir `"theme"`
   (default `"dark"` si falta la clave). No requiere `save_theme()` en esta spec.
   Prueba manual: borrar/editar `config.json` sin la clave `"theme"` y confirmar que
   `load_config()` devuelve `"dark"` igual.
3. **View — `ocr_view.py`.** Crear `OcrView(QWidget)` con paridad de widgets respecto a
   la `MainView` actual (abrir imagen, combobox idioma, transcribir, preview, resultado)
   más el botón "Volver", usando widgets PySide6. Mismos setters/getters que hoy expone
   `MainView` para no romper el contrato con `OcrController`.
   Prueba manual: instanciar `OcrView` sola en una ventana de prueba y verificar que se
   ven todos los widgets.
4. **View — `home_view.py`.** Crear `HomeView(QWidget)` con el botón "OCR de imágenes"
   habilitado y los placeholders deshabilitados. Expone una señal (ej.
   `ocr_selected = Signal()`) al hacer click en la opción habilitada.
   Prueba manual: instanciar `HomeView` sola y verificar que el botón habilitado emite la
   señal y los placeholders están deshabilitados.
5. **View — `main_window.py`.** Crear `MainWindow(QMainWindow)` con un `QStackedWidget`
   que aloja `HomeView` (índice 0) y `OcrView` (índice 1). Fija tamaño default 1200x900 y
   mínimo 600x400. Conecta la señal de `HomeView` para cambiar al índice de `OcrView`, y
   el botón "Volver" de `OcrView` para cambiar de vuelta al índice de `HomeView`. Aplica
   el tema oscuro fijo (paleta/QSS) a toda la ventana según `config_model.load_config()`.
   Prueba manual: arrancar la ventana, confirmar tamaño/mínimo correctos, navegar
   Home→OCR→Home con los botones, y que el tema oscuro se ve aplicado en toda la
   ventana.
6. **Controller — migrar `ocr_controller.py` a PySide6.** Cambiar `OcrController` para
   conectarse a los widgets de `OcrView` (señales `clicked`/`currentTextChanged` de Qt en
   vez de `command=` de Tkinter). Reemplazar `tkinter.filedialog`/`messagebox` por
   `QFileDialog`/`QMessageBox` en los flujos de abrir imagen, pedir ruta de Tesseract
   manual y mostrar errores.
   Prueba manual: repetir el flujo completo de la spec 01 (abrir imagen válida/inválida,
   transcribir, flujo de "Tesseract no encontrado") ahora sobre PySide6.
7. **Controller — threading con `QThread` + señales.** Reemplazar el
   `threading.Thread` + `view.after(200, ...)` actual por un `QThread` (o
   `QRunnable`/`QThreadPool`) que emite señales para actualizar el contador de segundos
   cada ~200ms (vía `QTimer` en el hilo principal) y el resultado final al terminar
   (éxito o error), deshabilitando/reactivando el botón "Transcribir" igual que hoy.
   Prueba manual: cargar una imagen grande (spec 02), confirmar que el contador de
   segundos sube visiblemente, la ventana sigue respondiendo, y no se puede disparar una
   segunda transcripción en paralelo.
8. **`main.py`.** Reemplazar el arranque de Tkinter por `QApplication` + `MainWindow` +
   `app.exec()`.
   Prueba: `python main.py` abre la ventana en el menú de inicio, con tema oscuro y
   tamaño 1200x900.
9. **Limpieza.** Eliminar `view/main_view.py` (reemplazado por los tres archivos nuevos)
   y cualquier import de `tkinter` remanente en el proyecto.
   Prueba: `grep -r "tkinter" .` (excluyendo `.git`) no devuelve resultados en código
   fuente del proyecto.
10. **Verificación end-to-end.** Repetir manualmente los flujos completos de las specs
    01, 02 y 03 (imagen simple, imagen grande con tiling, imagen con fondo complejo) ya
    sobre la app en PySide6, confirmando paridad funcional completa.

## Acceptance criteria

- [ ] `PySide6` está en `requirements.txt` y `python -c "import PySide6"` corre sin
      error.
- [ ] `python main.py` abre una única ventana de tamaño 1200x900 (mínimo 600x400) con
      tema oscuro aplicado, mostrando el menú de inicio.
- [ ] El menú de inicio muestra el botón "OCR de imágenes" habilitado y al menos un
      placeholder deshabilitado para futuras opciones.
- [ ] Al hacer click en "OCR de imágenes", la misma ventana cambia su contenido a la
      vista de OCR (sin abrir una ventana nueva, sin cambiar de tamaño).
- [ ] La vista de OCR tiene un botón "Volver" que regresa al menú de inicio en la misma
      ventana.
- [ ] La vista de OCR tiene paridad funcional completa con la `MainView` de Tkinter:
      abrir imagen, selector de idioma (Español/Inglés/Ambos), transcribir, preview,
      área de resultado.
- [ ] El flujo de "Tesseract no encontrado" (pedir ruta manual, persistir en
      `config.json`) sigue funcionando igual, usando `QFileDialog`/`QMessageBox`.
- [ ] Durante la transcripción, el botón "Transcribir" se deshabilita, se muestra
      `Procesando... Ns` actualizándose cada ~200ms vía señales de `QThread`, la ventana
      sigue respondiendo, y no se puede disparar una segunda transcripción en paralelo.
- [ ] El tiling de imágenes grandes (spec 02) y el preprocesamiento multi-variante (spec
      03) siguen funcionando sin cambios de comportamiento, verificado con imágenes de
      prueba de ambas specs.
- [ ] `config.json` incluye la clave `"theme"` con valor `"dark"`; si no existía la
      clave en un archivo previo, `load_config()` la asume igual sin error.
- [ ] No queda ningún import de `tkinter` en el código fuente del proyecto
      (`view/main_view.py` eliminado).
- [ ] MVC respetado: el Model no importa PySide6 ni Tkinter; `OcrController` no llama a
      `pytesseract` directamente; las vistas no llaman a `pytesseract` directamente.

## Decisions

- **Sí:** migrar a PySide6 en vez de PyQt6. Licencia LGPL (más permisiva que la GPL/
  comercial de PyQt6) para un proyecto que puede distribuirse sin ataduras de licencia.
- **Sí:** una única ventana (`QMainWindow` + `QStackedWidget`) en vez de abrir ventanas
  nuevas por pantalla. Pedido explícito del usuario; además evita gestionar el ciclo de
  vida de múltiples ventanas.
- **Sí:** tamaño de ventana fijo (1200x900 / min 600x400) en ambas pantallas, en vez de
  redimensionar según el contenido. Mantiene una experiencia predecible y reutiliza el
  tamaño ya validado en las specs 01-03.
- **Sí:** placeholders deshabilitados en el menú de inicio para opciones futuras, en vez
  de mostrar solo el botón de OCR de imágenes. Deja el layout preparado visualmente para
  cuando se agreguen specs futuras (OCR en vivo, ICR) sin rehacer `HomeView`.
- **Sí:** botón "Volver" en la vista de OCR. Permite al usuario cambiar de opción sin
  reiniciar la app, consistente con la idea de "una única ventana que cambia según las
  opciones elegidas".
- **Sí:** mismo `OcrController`, sin agregar un `AppController` de navegación dedicado.
  Con una sola opción de menú, la navegación es trivial (cambiar de índice en el
  `QStackedWidget`); un controller separado sería sobre-ingeniería para el alcance
  actual. Se puede extraer más adelante si la navegación crece en complejidad.
- **Sí:** `Pillow` se mantiene para decodificación/preview en vez de migrar a
  `QImage`/`QPixmap`. Minimiza el riesgo de la migración al no tocar `model/` ni el
  pipeline de preprocesamiento (specs 02/03), que ya asume objetos `Image.Image` de
  Pillow.
- **Sí:** threading con `QThread` + señales en vez de mantener `threading.Thread` +
  polling. Es el patrón idiomático y thread-safe de Qt para actualizar UI desde un hilo
  secundario; evita el polling manual que la spec 02 necesitó por limitaciones de
  Tkinter.
- **Sí:** `QFileDialog`/`QMessageBox` como reemplazo directo de los diálogos de Tkinter,
  sin diálogos custom. Mantiene el MVP simple y con comportamiento equivalente al
  actual.
- **Sí:** tema oscuro fijo, con clave `"theme"` en `config.json` (default `"dark"`) pero
  sin toggle de UI todavía. El toggle real queda diferido a una futura spec de "menú de
  opciones"; agregar la clave ahora evita un cambio de esquema de `config.json` en esa
  spec futura.
- **No:** tema claro o cualquier paleta alternativa en esta spec. Solo existe la paleta
  oscura; agregar una segunda paleta sin un toggle que la exponga no aporta valor ahora.
- **No:** empaquetar la app (PyInstaller u otro) como parte de esta spec. Fuera de
  alcance declarado desde el MVP original.

## Risks

| Risk | Mitigation |
|---|---|
| `PySide6` es una dependencia pesada (~150-200MB con Qt embebido), puede complicar la instalación en la máquina del usuario o alargar el setup del entorno. | Decisión consciente ya tomada; se documenta en `requirements.txt`. Es el costo esperado de tener una GUI más capaz que Tkinter. |
| El paso de `threading.Thread` + polling a `QThread` + señales puede introducir bugs sutiles de threading (ej. actualizar un widget fuera del hilo principal) si no se usan señales para toda comunicación entre hilos. | El paso 7 del plan de implementación exige explícitamente usar señales para toda actualización de UI, replicando la disciplina que ya impuso `view.after(...)` en la spec 02. |
| Migrar el manejo de errores (spec 01, paso 9) a `QMessageBox` podría perder algún caso borde cubierto hoy por los diálogos de Tkinter si no se revisan todos los `except` existentes. | El paso 6 del plan pide repetir explícitamente el flujo completo de errores de la spec 01 como prueba manual antes de dar el paso por cerrado. |
| El tema oscuro fijo (QSS/paleta) puede dejar algún widget con contraste pobre o ilegible si no se prueba visualmente cada pantalla. | El paso 5 del plan incluye una verificación visual manual de que el tema se aplica correctamente en toda la ventana, no solo en los widgets principales. |
| Aplicar un stylesheet QSS global podría interferir con el look nativo de `QFileDialog`/`QMessageBox` en algunos sistemas operativos. | Se acepta como riesgo conocido de bajo impacto (son diálogos modales de uso puntual); si se nota mal contraste, se puede excluir el QSS de esos diálogos en la implementación. |
