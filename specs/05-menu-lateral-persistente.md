# SPEC 05 — Menú lateral persistente en la ventana principal

> **Status:** Implementado
> **Depends on:** `specs/04-migracion-pyside6-menu-inicio.md`
> **Date:** 2026-07-12
> **Objective:** Reemplazar la pantalla de inicio de pantalla completa por un layout persistente con un menú lateral (sidebar) siempre visible y un área de contenido central que cambia según la opción seleccionada, con OCR de imágenes activo por default.

## Scope

**In:**

- **`view/home_view.py` se renombra a `view/sidebar_view.py`**, y la clase `HomeView` pasa a llamarse `SidebarView(QWidget)`. Mantiene los mismos dos botones ("OCR de imágenes" habilitado, "OCR en vivo" deshabilitado) pero en un layout vertical angosto pensado para ser un panel lateral fijo, no una pantalla completa.
- **`SidebarView` resalta visualmente la opción activa** (el botón de la opción actualmente seleccionada en el área de contenido) usando el mismo azul ya definido en `DARK_PALETTE[QPalette.Highlight]` (`QColor(42, 130, 218)`) de `main_window.py`, vía el estado `checked` de `QPushButton` (botones tipo toggle/checkable).
- **`view/main_window.py` cambia su estructura interna:** en vez de un único `QStackedWidget` de pantalla completa con `HomeView`/`OcrView`, pasa a un layout horizontal fijo con dos zonas siempre visibles:
  - Izquierda: `SidebarView`, ancho fijo (ej. 200px).
  - Derecha: un `QStackedWidget` de contenido que aloja `OcrView` (índice 0, activo por default al arrancar). Queda preparado para agregar futuras vistas (ej. "OCR en vivo") en próximos índices.
- **Se elimina el botón "Volver" de `OcrView`** (y la señal `back_requested`), ya que deja de tener sentido con el sidebar siempre visible.
- **Tamaño de ventana fijo simple:** `MainWindow` usa `setFixedSize(1200, 900)` en vez del actual `resize` + `setMinimumSize(600, 400)`. El botón de maximizar queda deshabilitado por el propio SO (comportamiento estándar de Qt para ventanas de tamaño fijo); esto se documenta como decisión consciente, no como bug.
- El título de la ventana se mantiene igual: `"OCR"` (sin cambios, pendiente de definir un nombre mejor en una futura spec).

**Out (para futuras specs):**

- Implementar la opción "OCR en vivo" (sigue como placeholder deshabilitado en el sidebar).
- Redefinir el nombre del proyecto/ventana.
- Toggle de tema claro/oscuro o cualquier opción de configuración visual nueva.
- Redimensionar la ventana en modo ventana (ventana fija, solo maximizar/restaurar disponible vía el SO, sin controles custom adicionales).
- Rediseño visual pulido más allá de mover elementos a la nueva estructura (sigue la filosofía de interfaz funcional).

## Data model

No se agregan ni modifican estructuras de datos persistidas (`config.json` no cambia respecto a la spec 04). Se documentan las clases nuevas/renombradas en `view/`:

```python
class SidebarView(QWidget):
    """Panel lateral fijo: botón 'OCR de imágenes' (habilitado, checkable) y
    'OCR en vivo' (deshabilitado, placeholder). Resalta el botón de la opción
    activa. Emite una señal al elegir una opción habilitada. No contiene
    lógica de negocio."""

    ocr_selected = Signal()


class MainWindow(QMainWindow):
    """Ventana única de tamaño fijo (1200x900, setFixedSize). Layout horizontal
    con SidebarView (ancho fijo) a la izquierda y un QStackedWidget de
    contenido a la derecha (OcrView en el índice 0, activo por default).
    Conecta la señal de SidebarView para cambiar de índice en el stack de
    contenido y sincronizar el estado 'checked' del botón activo."""
```

`OcrView` pierde el atributo `back_button` y la señal `back_requested`; el resto de su contrato (widgets, setters/getters) no cambia.

## Implementation plan

1. **Renombrar `view/home_view.py` → `view/sidebar_view.py`.** Renombrar la clase `HomeView` a `SidebarView`. Convertir `ocr_button` en un `QPushButton` checkable (`setCheckable(True)`, `setChecked(True)` por default ya que "OCR de imágenes" arranca activo). Agregar un estilo QSS/paleta para el estado `checked` usando el azul `QColor(42, 130, 218)`.
   Prueba manual: instanciar `SidebarView` sola en una ventana de prueba, confirmar que el botón "OCR de imágenes" se ve resaltado por default y "OCR en vivo" sigue deshabilitado.

2. **`view/ocr_view.py`: eliminar botón "Volver".** Quitar `back_button`, la señal `back_requested` y su conexión.
   Prueba manual: instanciar `OcrView` sola, confirmar que ya no aparece el botón "Volver" y el resto de widgets sigue igual.

3. **`view/main_window.py`: nueva estructura de layout.** Reemplazar el `QStackedWidget` de pantalla completa por un `QHBoxLayout` con `SidebarView` (ancho fijo ~200px) a la izquierda y un `QStackedWidget` de contenido a la derecha que aloja `OcrView` en el índice 0. Cambiar `resize(...)` + `setMinimumSize(...)` por `setFixedSize(1200, 900)`. Conectar `SidebarView.ocr_selected` para cambiar el índice del stack de contenido (hoy solo hay un índice, pero se deja la conexión lista). Eliminar la conexión a `ocr_view.back_requested` (ya no existe).
   Prueba manual: `python main.py` abre la ventana con sidebar a la izquierda y `OcrView` visible por default a la derecha; intentar redimensionar arrastrando el borde no tiene efecto; maximizar funciona y usa toda la pantalla; el botón "OCR de imágenes" aparece resaltado en el sidebar.

4. **`controller/ocr_controller.py`: verificar referencias.** Confirmar que `OcrController` no referencia `back_button`/`back_requested` ni otros atributos eliminados (no debería, ya que esa lógica vivía en `MainWindow`, pero se revisa por las dudas).
   Prueba manual: repetir el flujo completo de OCR (abrir imagen, seleccionar idioma, transcribir) y confirmar que sigue funcionando igual que antes del cambio de layout.

5. **Limpieza y verificación end-to-end.** Confirmar que no queda ningún import ni referencia a `HomeView`/`home_view.py` en el proyecto (`grep -r "HomeView\|home_view" .` sin resultados fuera de este archivo de spec y de la spec 04 histórica).
   Prueba: `python main.py`, verificar layout completo (sidebar + contenido), tamaño fijo, resaltado del botón activo, y flujo de OCR de imágenes funcionando de punta a punta.

## Acceptance criteria

- [ ] `python main.py` abre una ventana de tamaño fijo 1200x900 (no redimensionable manualmente arrastrando el borde), con maximizar habilitado y funcional (usa toda la pantalla).
- [ ] La ventana muestra siempre visibles un sidebar a la izquierda (`SidebarView`) y un área de contenido a la derecha, sin necesidad de navegar entre "pantallas".
- [ ] El sidebar muestra el botón "OCR de imágenes" habilitado y "OCR en vivo" deshabilitado, igual que antes.
- [ ] Al arrancar la app, el área de contenido muestra `OcrView` por default y el botón "OCR de imágenes" del sidebar aparece resaltado (checked) con el azul `QColor(42, 130, 218)`.
- [ ] `view/home_view.py` ya no existe; fue reemplazado por `view/sidebar_view.py` con la clase `SidebarView`.
- [ ] `OcrView` ya no tiene botón "Volver" ni señal `back_requested`.
- [ ] El flujo completo de OCR de imágenes (abrir imagen, seleccionar idioma, transcribir, preview, resultado) sigue funcionando igual que antes del cambio de layout.
- [ ] No queda ninguna referencia a `HomeView`/`home_view.py`/`back_button`/`back_requested` en el código fuente del proyecto.
- [ ] MVC respetado: `SidebarView` y `MainWindow` no llaman a `pytesseract` directamente; no hay lógica de negocio en las vistas.

## Decisions

- **Sí:** renombrar `HomeView`/`home_view.py` a `SidebarView`/`sidebar_view.py` en vez de crear un archivo nuevo y dejar el viejo obsoleto. Evita duplicar el concepto de "menú de opciones" en dos archivos distintos.
- **Sí:** mantener un `QStackedWidget` en el área de contenido desde ya (aunque hoy solo tenga `OcrView` cargada), en vez de mostrar `OcrView` como widget fijo sin stack. Pedido explícito del usuario para facilitar agregar futuras opciones (ej. "OCR en vivo") sin rehacer `MainWindow`.
- **Sí:** eliminar el botón "Volver" y su señal, en vez de mantenerlo sin uso. Con el sidebar siempre visible, cambiar de opción es simplemente clickear otro ítem del sidebar; mantener "Volver" sería un control redundante y confuso.
- **Sí:** tamaño de ventana fijo simple (`setFixedSize`) en vez de interceptar eventos de resize para permitir maximizar con tamaño de ventana bloqueado. Es la opción más simple y estándar de Qt; el usuario aceptó el trade-off de que el botón de maximizar del SO quede deshabilitado.
- **Sí:** resaltado del botón activo usando el azul ya definido en `DARK_PALETTE[QPalette.Highlight]`. El usuario está conforme con el color; si no convence visualmente al verlo implementado, se ajusta dentro del mismo `spec-impl` en vez de diferirlo a una spec futura.
- **Sí:** ancho del sidebar fijo en píxeles (no proporcional al ancho de la ventana), consistente con que toda la ventana ahora es de tamaño fijo.
- **No:** renombrar el proyecto o cambiar el título de la ventana en esta spec. El usuario mencionó que el proyecto "dejó de ser un MVP", pero decidió dejar el título `"OCR"` como está por ahora; un posible renombre queda para una spec futura.
- **No:** implementar la opción "OCR en vivo" en esta spec. Sigue como placeholder deshabilitado en el sidebar.

## Risks

| Risk | Mitigation |
|---|---|
| `setFixedSize` deshabilita el botón de maximizar en algunos entornos/gestores de ventanas (comportamiento depende del SO), lo cual contradice parcialmente el pedido de "que maximizar sí funcione". | Decisión consciente del usuario (opción recomendada); si en la verificación manual (paso 3 del plan) se confirma que maximizar no funciona en el entorno de desarrollo real, se documenta como limitación conocida de Qt en vez de agregar lógica custom de resize. |
| Convertir `ocr_button` en checkable podría introducir un bug donde el botón quede "sin seleccionar" si el usuario hace click sobre un botón ya activo (comportamiento por default de `QPushButton` checkable permite des-chequear). | El paso 1 del plan pide verificar manualmente que "OCR de imágenes" quede siempre resaltado al arrancar; si aparece el bug, se fuerza `setChecked(True)` tras cualquier intento de des-chequeo (grupo exclusivo de un solo botón). |
