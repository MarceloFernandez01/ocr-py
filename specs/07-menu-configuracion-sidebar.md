# SPEC 07 — Menú de configuración en el sidebar

> **Status:** Aprobado
> **Depends on:** `specs/06-reskin-metro.md`
> **Date:** 2026-07-12
> **Objective:** Agregar un botón de engranaje al fondo del sidebar que navega a una nueva vista de Configuración, con un toggle funcional de tema claro/oscuro y un placeholder deshabilitado para el motor OCR.

## Scope

**In:**

- **`view/sidebar_view.py`**: se agrega un botón de engranaje (`⚙`, glifo unicode) al fondo del sidebar, separado de "OCR de imágenes"/"OCR en vivo" por un `addStretch()`. Es checkable, mutuamente excluyente con los demás tiles (solo uno resaltado a la vez), y emite una nueva señal `settings_selected`.
- **Nuevo `view/settings_view.py`** (`SettingsView(QWidget)`): vista de contenido (análoga a `OcrView`) con:
  - Un `QPushButton` checkable estilo switch ("Modo claro") para alternar tema. Refleja el estado actual del tema al construirse. Emite `theme_toggled(str)` con `"dark"` o `"light"` al hacer click.
  - Un `QComboBox` deshabilitado con dos ítems: `"Tesseract"` (seleccionado) y `"Claude Haiku (próximamente)"` (presente en la lista pero no seleccionable porque el combobox entero está deshabilitado).
- **`view/metro_style.py` ampliado**: se agrega una variante clara del stylesheet (`METRO_STYLESHEET_LIGHT`) espejando la estructura de la actual (que pasa a llamarse `METRO_STYLESHEET_DARK`), con fondo blanco/gris claro, texto oscuro y el mismo acento azul `rgb(42,130,218)`. Se agrega una función `get_stylesheet(theme: str) -> str` que devuelve la variante correspondiente.
- **`model/config_model.py`**: nueva función `save_theme(theme: str) -> None` que persiste la clave `"theme"` en `config.json`.
- **Nuevo `controller/settings_controller.py`** (`SettingsController`): escucha `SettingsView.theme_toggled`, llama a `save_theme()` del model, y reaplica el tema en caliente sobre la ventana (paleta + stylesheet) sin reiniciar la app.
- **`view/main_window.py`**: agrega `SettingsView` al `content_stack` (nuevo índice), conecta `sidebar_view.settings_selected` para navegar a esa vista, instancia `SettingsController`, y expone un método para reaplicar tema (usado por el controller) — ej. `apply_theme(theme: str)` que reemplaza `apply_dark_theme` actual.
- El toggle de tema aplica **en caliente**: al tildar/destildar el switch, la ventana entera cambia de paleta/stylesheet inmediatamente, sin reiniciar `python main.py`.

**Out (para futuras specs):**

- Cambiar el motor OCR de Tesseract a Claude Haiku u otro modelo real (el combobox es 100% placeholder visual, sin lógica).
- Cualquier otra opción de configuración además de tema y el placeholder de motor OCR (ej. idioma default, atajos, etc.).
- Rediseño de íconos custom dibujados (se usa el glifo unicode `⚙`, no un ícono vectorial).
- Persistir o afectar el tema de `QFileDialog`/`QMessageBox` (siguen nativos, sin cambios respecto a spec 06).

## Data model

```python
# view/settings_view.py

class SettingsView(QWidget):
    """Vista de contenido con las opciones de configuración: toggle de tema
    claro/oscuro y placeholder deshabilitado del motor OCR. No contiene
    lógica de negocio ni persiste nada directamente; emite `theme_toggled`
    para que el controller decida qué hacer."""

    theme_toggled = Signal(str)  # "dark" | "light"

    def set_theme(self, theme: str) -> None:
        """Sincroniza el estado visual del switch con el tema actual,
        sin emitir `theme_toggled` (evita loops al llamarse desde el controller)."""
```

```python
# view/sidebar_view.py (ampliación)

class SidebarView(QWidget):
    ocr_selected = Signal()
    settings_selected = Signal()  # nueva señal

    # self.settings_button: QPushButton checkable, objectName "sidebarTile",
    # glifo "⚙", ubicado al fondo tras un addStretch().
    # Mutuamente excluyente con ocr_button/live_ocr_button.
```

```python
# view/metro_style.py (ampliación)

METRO_STYLESHEET_DARK: str   # renombre del actual METRO_STYLESHEET
METRO_STYLESHEET_LIGHT: str  # espejo claro: fondo blanco/gris claro, texto oscuro, mismo ACCENT

def get_stylesheet(theme: str) -> str:
    """Devuelve METRO_STYLESHEET_DARK o METRO_STYLESHEET_LIGHT según `theme`
    ("dark"/"light"). Sin lógica de negocio, solo selección de presentación."""
```

```python
# model/config_model.py (ampliación)

def save_theme(theme: str) -> None:
    """Persiste `theme` ("dark" o "light") en config.json, preservando el resto de claves existentes."""
```

```python
# controller/settings_controller.py

class SettingsController:
    """Conecta SettingsView con el Model: al recibir `theme_toggled`, llama a
    save_theme() y le pide a MainWindow reaplicar el tema en caliente
    (paleta + stylesheet) sobre toda la ventana."""

    def __init__(self, settings_view: SettingsView, main_window: MainWindow) -> None: ...
```

`config.json` no agrega claves nuevas (`theme` ya existía desde spec 04, hoy sin escritor); solo se agrega el escritor `save_theme()`.

## Implementation plan

1. **`model/config_model.py`: agregar `save_theme(theme)`.** Análoga a `save_tesseract_path`: carga config existente, setea `config["theme"] = theme`, escribe el JSON completo.
   Prueba manual: `python -c "from model.config_model import save_theme; save_theme('light')"`, confirmar que `config.json` queda con `"theme": "light"` y el resto de claves intactas.

2. **`view/metro_style.py`: renombrar y agregar variante clara.** Renombrar `METRO_STYLESHEET` → `METRO_STYLESHEET_DARK`. Escribir `METRO_STYLESHEET_LIGHT` espejando la misma estructura de selectores (mismo `ACCENT`, mismos `objectName`s como `sidebarTile`/`previewLabel`/`sidebarSeparator`) pero con fondo claro (ej. `rgb(240,240,240)` general, `rgb(255,255,255)` para superficies tipo `QTextEdit`/preview) y texto oscuro (`rgb(20,20,20)`). Agregar `get_stylesheet(theme: str) -> str`.
   Prueba: `python -c "from view.metro_style import get_stylesheet; print(len(get_stylesheet('light')))"` sin error; revisar visualmente que no queden textos negros sobre fondos negros ni blancos sobre blancos comparando ambas constantes lado a lado.

3. **`view/sidebar_view.py`: agregar botón de engranaje.** Agregar `settings_button` (`QPushButton("⚙")`, `objectName="sidebarTile"`, checkable) al final del layout, después de un `addStretch()` que empuja "OCR de imágenes"/"OCR en vivo" hacia arriba. Extender la lógica de exclusividad actual (`_on_ocr_button_clicked`) para que sea genérica entre los tres botones (`ocr_button`, `live_ocr_button` si algún día se habilita, `settings_button`): al clickear uno, se marca `checked=True` y los demás `checked=False`. Emitir `settings_selected` al clickear el engranaje.
   Prueba manual: instanciar `SidebarView` sola, confirmar que el engranaje aparece al fondo del sidebar, que clickearlo lo resalta en azul y destilda "OCR de imágenes", y viceversa.

4. **Nuevo `view/settings_view.py`.** Crear `SettingsView(QWidget)` con: `QPushButton("Modo claro")` checkable estilo switch (`objectName` propio para QSS, ej. `themeSwitch`) y `QComboBox` deshabilitado con ítems `"Tesseract"` y `"Claude Haiku (próximamente)"` (índice 0 seleccionado). Exponer `theme_toggled(str)` (emite `"light"` si `checked`, `"dark"` si no) y `set_theme(theme: str)` para sincronizar el switch sin re-emitir la señal (usar `blockSignals` alrededor de `setChecked`).
   Prueba manual: instanciar `SettingsView` sola, confirmar que el switch arranca destildado (dark default), el combobox se ve deshabilitado con "Tesseract" visible, y clickear el switch emite la señal esperada (imprimir en un slot de prueba).

5. **`view/metro_style.py`: estilos del switch y del combobox deshabilitado.** Agregar reglas QSS para `QPushButton#themeSwitch` (checked = bloque de acento, texto indicando estado) y reforzar que `QComboBox:disabled` se vea legible en ambos temas (texto atenuado pero visible, no invisible).
   Prueba manual: alternar el switch en `SettingsView` aislada y confirmar contraste aceptable en ambos estados.

6. **`view/main_window.py`: refactor de aplicación de tema + integración de `SettingsView`.** Reemplazar `apply_dark_theme`/uso directo de `DARK_PALETTE`+`METRO_STYLESHEET` por un método `apply_theme(theme: str)` que arma la paleta correspondiente (clara u oscura) y llama a `get_stylesheet(theme)` para el QSS, aplicando ambos sobre `self`. Instanciar `SettingsView`, agregarla al `content_stack` (índice 1), conectar `sidebar_view.settings_selected` para navegar a ella. Instanciar `SettingsController(settings_view, main_window)`. Al arrancar, llamar `apply_theme(config["theme"])` y `settings_view.set_theme(config["theme"])`.
   Prueba manual: `python main.py`, confirmar que arranca en oscuro, navegar a Configuración vía el engranaje, alternar el switch y ver la ventana completa (sidebar, separador, área de contenido) cambiar a claro en caliente sin reiniciar; volver a oscuro y confirmar que también funciona.

7. **Nuevo `controller/settings_controller.py`.** Crear `SettingsController` que conecta `settings_view.theme_toggled` a un handler: llama `save_theme(theme)` del model y `main_window.apply_theme(theme)`. Instanciarlo en `main_window.py` (paso 6).
   Prueba manual: alternar el switch, cerrar la app, reabrir con `python main.py`, confirmar que arranca con el último tema elegido (persistencia via `config.json`) y que el switch en `SettingsView` refleja ese estado al entrar a Configuración.

8. **Verificación end-to-end.** Confirmar que el flujo completo de OCR (abrir imagen, idioma, transcribir, preview, resultado) sigue funcionando igual en ambos temas; que la exclusividad de los tres botones del sidebar funciona en cualquier combinación de clicks; que no queda ningún `setStyleSheet` disperso fuera de `metro_style.py`; y que `grep -r "METRO_STYLESHEET\b"` (sin sufijo `_DARK`/`_LIGHT`) no da resultados fuera de este archivo de spec.
   Prueba: recorrido manual completo descrito arriba + revisión de imports rotos.

## Acceptance criteria

- [ ] El sidebar muestra un botón de engranaje (`⚙`) al fondo, separado de "OCR de imágenes"/"OCR en vivo" por espacio (stretch).
- [ ] Clickear el engranaje navega al área de contenido a la nueva vista `SettingsView`, resaltando el engranaje en azul y destildando cualquier otro tile del sidebar.
- [ ] Clickear "OCR de imágenes" desde Configuración vuelve a `OcrView` y destilda el engranaje (exclusividad mutua verificada en ambas direcciones).
- [ ] `SettingsView` muestra un switch "Modo claro" y un `QComboBox` deshabilitado con `"Tesseract"` seleccionado y `"Claude Haiku (próximamente)"` visible pero no seleccionable.
- [ ] Al tildar el switch, toda la ventana (sidebar, separador, área de contenido, widgets de `OcrView` y `SettingsView`) cambia a tema claro **inmediatamente**, sin reiniciar `python main.py`.
- [ ] Al destildar el switch, la ventana vuelve a tema oscuro en caliente.
- [ ] El tema elegido se persiste en `config.json` bajo la clave `"theme"` (`"dark"`/`"light"`); reabrir la app con `python main.py` arranca con el último tema guardado.
- [ ] Al entrar a `SettingsView`, el switch refleja el tema actual de la ventana (no arranca siempre destildado si el tema guardado es claro).
- [ ] El flujo completo de OCR (abrir imagen, seleccionar idioma, transcribir, preview, resultado) funciona igual en ambos temas, sin regresiones.
- [ ] No hay texto ilegible (bajo contraste) en ningún widget bajo el tema claro ni el oscuro.
- [ ] MVC respetado: `SettingsView`/`SidebarView` no llaman a `save_theme()` ni a lógica de negocio directamente; `SettingsController` es quien conecta la señal con el model y con `MainWindow.apply_theme()`.
- [ ] `model/config_model.py` expone `save_theme(theme: str)` y persiste correctamente sin perder otras claves de `config.json` (ej. `tesseract_path`).
- [ ] No queda ninguna referencia a `METRO_STYLESHEET` (sin sufijo) en el código fuente; solo `METRO_STYLESHEET_DARK`, `METRO_STYLESHEET_LIGHT` y `get_stylesheet()`.

## Decisions

- **Sí:** representar Configuración como una vista dentro del `content_stack` (igual patrón que `OcrView`) en vez de un `QMenu` popup o un `QDialog` modal. Mantiene consistencia con la navegación ya existente del sidebar y evita introducir un segundo paradigma de UI (menús contextuales) al proyecto.
- **Sí:** botón de engranaje checkable y mutuamente excluyente con los demás tiles del sidebar, igual que "OCR de imágenes"/"OCR en vivo". Reutiliza el patrón ya validado en spec 05, sin inventar un estado visual nuevo.
- **Sí:** usar el glifo unicode `⚙` como ícono en vez de un ícono vectorial dibujado o un asset de imagen. Cero dependencias nuevas, consistente con la restricción del proyecto de evitar módulos externos; con Segoe UI (spec 06) se renderiza como un engranaje reconocible en Windows.
- **Sí:** aplicar el cambio de tema en caliente (paleta + QSS reaplicados sobre la ventana ya abierta) en vez de requerir reinicio. Mejor UX, viable de forma simple porque `QWidget.setPalette`/`setStyleSheet` se pueden volver a invocar en cualquier momento.
- **Sí:** introducir `controller/settings_controller.py` en vez de manejar el guardado/aplicado de tema directo en `MainWindow`. Mantiene la lógica de orquestación (llamar al model, decidir cuándo reaplicar) fuera de la vista, siguiendo el mismo patrón que `OcrController`, aunque `MainWindow` ya lee `load_config()` directamente al arrancar (precedente existente que no se toca).
- **Sí:** tema claro como espejo estructural del QSS oscuro actual (mismos selectores/objectNames, mismo acento `rgb(42,130,218)`), en vez de un diseño visual nuevo. Minimiza riesgo de inconsistencias entre temas y reutiliza el trabajo de spec 06.
- **Sí:** el combobox de motor OCR lista ambas opciones (`Tesseract` y `Claude Haiku (próximamente)`) pero deshabilitado por completo, en vez de mostrar una sola opción o un texto plano. Comunica visualmente el roadmap sin implementar lógica real, cumpliendo el pedido explícito del usuario de dejarlo como placeholder.
- **No:** implementar el cambio real de motor OCR (Tesseract → Claude Haiku) en esta spec. Placeholder puro, sin lógica; queda para una spec futura cuando se decida cómo integrar un motor basado en modelo.
- **No:** estilar `QFileDialog`/`QMessageBox` para el tema claro. Se mantiene la decisión de spec 06 de dejarlos nativos, sin excepción por el nuevo tema.
- **No:** agregar más opciones de configuración (idioma default, atajos, etc.) más allá de tema y el placeholder de motor OCR. Fuera de alcance explícito del pedido original.

## Risks

| Risk | Mitigation |
|---|---|
| El QSS claro nuevo (`METRO_STYLESHEET_LIGHT`) puede dejar algún widget con bajo contraste si se olvida espejar un selector del oscuro (ej. `QComboBox:disabled`, `QTextEdit:focus`). | El paso 2 del plan pide comparar ambas constantes selector por selector; el paso 8 exige una revisión visual completa de `OcrView` y `SettingsView` bajo ambos temas antes de cerrar. |
| Reaplicar paleta + stylesheet en caliente sobre una ventana ya renderizada puede dejar algún widget hijo con estilos "pegados" del tema anterior si Qt no repinta correctamente. | El paso 6 incluye probar manualmente el toggle ida y vuelta (oscuro→claro→oscuro) varias veces, no solo una vez, para detectar residuos visuales. |
| Generalizar la exclusividad mutua a tres botones (`ocr_button`, `live_ocr_button`, `settings_button`) puede introducir un bug donde clickear el botón deshabilitado ("OCR en vivo") rompa el estado checked de los otros dos. | El paso 3 prueba explícitamente las combinaciones de clicks entre los tres botones, incluyendo confirmar que "OCR en vivo" sigue deshabilitado y no participa de la lógica de toggle. |
| `SettingsController` reaplicando tema podría crear un loop si `set_theme()` en `SettingsView` re-emite `theme_toggled` al sincronizar el switch. | El paso 4 exige usar `blockSignals` al llamar `setChecked` dentro de `set_theme()`, y el paso 7 verifica que alternar el switch no dispare llamadas duplicadas a `save_theme()`. |
| Persistir el tema con `save_theme()` podría pisar `tesseract_path` si la función reescribe el JSON completo en vez de mergear. | El paso 1 prueba explícitamente que otras claves de `config.json` (ej. `tesseract_path`) sobreviven después de llamar `save_theme()`, siguiendo el mismo patrón ya usado por `save_tesseract_path`. |
