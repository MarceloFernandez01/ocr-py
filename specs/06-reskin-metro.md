# SPEC 06 — Re-skin visual estilo Metro

> **Status:** Implementada
> **Depends on:** `specs/05-menu-lateral-persistente.md`
> **Date:** 2026-07-12
> **Objective:** Aplicar un re-skin visual estilo Metro (Modern UI) a toda la GUI —tipografía Segoe UI, superficies planas, color de acento y tiles— mediante un stylesheet QSS centralizado, sin modificar el layout ni la navegación actuales.

## Scope

**In:**

- **Nuevo módulo `view/metro_style.py`** (respeta MVC: solo presentación, sin lógica de negocio ni `pytesseract`). Expone el stylesheet QSS metro como constante (`METRO_STYLESHEET`) más las constantes visuales (`ACCENT = rgb(42,130,218)`, `FONT_FAMILY = Segoe UI`, tamaños/pesos). Es la única fuente del look metro; nada de `setStyleSheet` esparcido por widgets individuales.
- **`view/main_window.py` aplica el stylesheet metro una sola vez** a nivel aplicación (sobre la `QApplication`/`MainWindow`), junto con la paleta oscura existente. La paleta `DARK_PALETTE` se mantiene como base; el QSS metro se superpone.
- **Superficies re-estilizadas (skin metro oscuro):**
  - **Ventana / fondo general:** superficie plana oscura, sin bordes ni gradientes.
  - **`SidebarView`:** botones convertidos visualmente en tiles planos (rectangulares, sin bordes redondeados ni sombras); el estado `checked`/hover se muestra como bloque de acento sólido. Se conserva el botón habilitado, el placeholder deshabilitado y las señales actuales.
  - **`OcrView`:** botones (`Abrir imagen`, `Transcribir`), `QComboBox` de idioma, `QLabel` de preview y `QTextEdit` de resultado re-estilizados planos, con tipografía Segoe UI y acento en foco/hover.
- **Tipografía Segoe UI** aplicada globalmente vía el QSS, con títulos/botones en peso liviano y tamaño mayor al default.
- **Tema:** sigue siendo oscuro fijo (metro oscuro). No se agrega toggle ni tema claro.

**Out (para futuras specs):**

- **Estilado de `QFileDialog` / `QMessageBox`:** son diálogos nativos del SO; se dejan con su apariencia nativa. No se fuerza QSS sobre ellos en esta spec.
- **Cambios de layout / reordenamiento de widgets** (padding metro amplio, tiles cuadrados, agrandar preview/resultado, reubicar toolbars): esta spec es solo re-skin; se evaluará ajustar layouts en una spec futura si hace falta.
- **Tema claro / toggle de tema / menú de opciones visuales.**
- **Cambios funcionales** del flujo de OCR, sidebar o navegación (nada de comportamiento cambia; solo lo visual).

## Data model

Esta spec no introduce ni modifica estructuras de datos persistidas (`config.json` no cambia respecto a la spec 05; el tema sigue siendo `"dark"` fijo). Solo se documenta el módulo nuevo de presentación:

```python
# view/metro_style.py

ACCENT = "rgb(42, 130, 218)"   # mismo azul de DARK_PALETTE[QPalette.Highlight]
FONT_FAMILY = "Segoe UI"

METRO_STYLESHEET: str
"""Stylesheet QSS con el look metro (tipografía Segoe UI, superficies planas,
tiles del sidebar, acento en hover/checked/foco). Única fuente del skin metro;
se aplica una sola vez a nivel QApplication/MainWindow. Sin lógica de negocio,
no importa pytesseract (respeta MVC)."""
```

Las clases existentes (`MainWindow`, `SidebarView`, `OcrView`) no cambian su contrato (mismos widgets, señales, setters/getters). Solo `MainWindow` suma la línea que aplica `METRO_STYLESHEET`.

## Implementation plan

1. **Crear `view/metro_style.py`.** Definir las constantes (`ACCENT`, `FONT_FAMILY`) y el `METRO_STYLESHEET` (QSS) con: tipografía Segoe UI global, superficies planas (sin `border-radius` ni sombras), estilos base para `QPushButton`, `QComboBox`, `QTextEdit`, `QLabel`, y reglas de hover/foco con el acento azul. Sin lógica de negocio, sin importar `pytesseract`.
   Prueba: `python -c "from view.metro_style import METRO_STYLESHEET"` sin error.

2. **Aplicar el stylesheet en `view/main_window.py`.** Importar `METRO_STYLESHEET` y aplicarlo una sola vez (sobre `QApplication.instance()` o `self` en `MainWindow`), manteniendo la paleta oscura existente. No tocar el layout ni la navegación.
   Prueba manual: `python main.py` abre la ventana con la tipografía Segoe UI y superficies planas aplicadas en toda la GUI.

3. **Tiles del sidebar (`SidebarView`).** Ajustar el QSS para que los botones del sidebar se vean como tiles metro planos, con el estado `checked`/hover como bloque de acento sólido. Reemplaza al `CHECKED_BUTTON_STYLE` local actual (que pasa a vivir centralizado en `metro_style.py`, no en `sidebar_view.py`).
   Prueba manual: el botón "OCR de imágenes" se ve como tile resaltado por default; "OCR en vivo" sigue deshabilitado y visualmente atenuado.

4. **Verificar `OcrView` bajo el skin.** Confirmar que botones, combobox de idioma, preview y área de resultado se ven coherentes con el metro (planos, acento en foco/hover, legibles sobre fondo oscuro). Ajustes finos de QSS si algún widget queda con bajo contraste.
   Prueba manual: recorrer el flujo visual de `OcrView` (sin necesidad de transcribir) y confirmar coherencia metro.

5. **Limpieza y verificación end-to-end.** Quitar el `CHECKED_BUTTON_STYLE` remanente de `sidebar_view.py` si quedó duplicado; confirmar que no hay `setStyleSheet` esparcido fuera de `metro_style.py`. Correr el flujo completo de OCR (abrir imagen, idioma, transcribir, preview, resultado) para confirmar que nada funcional se rompió.
   Prueba: `python main.py`, verificar look metro en toda la GUI + flujo de OCR funcionando de punta a punta; `QFileDialog`/`QMessageBox` siguen con apariencia nativa (fuera de alcance).

## Acceptance criteria

- [x] Existe `view/metro_style.py` con `METRO_STYLESHEET` (y constantes `ACCENT`, `FONT_FAMILY`); `python -c "from view.metro_style import METRO_STYLESHEET"` corre sin error.
- [x] `view/main_window.py` aplica el stylesheet metro una sola vez a nivel aplicación; no hay `setStyleSheet` con QSS de skin esparcido en `sidebar_view.py`/`ocr_view.py`.
- [x] `python main.py` muestra toda la GUI con tipografía Segoe UI y superficies planas (sin bordes redondeados ni sombras).
- [x] Los botones del sidebar se ven como tiles metro planos; el botón activo ("OCR de imágenes") aparece resaltado como bloque de acento azul `rgb(42,130,218)` y "OCR en vivo" sigue deshabilitado y atenuado.
- [x] Botones, combobox, preview y área de resultado de `OcrView` se ven coherentes con el metro y legibles sobre fondo oscuro (sin bajo contraste).
- [x] El tema sigue siendo oscuro fijo (no hay toggle ni tema claro nuevo).
- [x] `QFileDialog`/`QMessageBox` conservan su apariencia nativa (no se estilan en esta spec).
- [x] El flujo completo de OCR (abrir imagen, idioma, transcribir, preview, resultado) funciona igual que antes del re-skin; ningún comportamiento funcional cambió.
- [x] MVC respetado: `metro_style.py` no importa `pytesseract`; las vistas no contienen lógica de negocio.

## Decisions

- **Sí:** centralizar todo el QSS en un módulo nuevo `view/metro_style.py` en vez de esparcir `setStyleSheet` por cada widget. Evita spaghetti, mantiene una única fuente de verdad del skin y respeta MVC (vive en `view/`, solo presentación). Pedido explícito del usuario.
- **Sí:** aplicar el stylesheet una sola vez a nivel `QApplication`/`MainWindow`, superponiéndolo a la `DARK_PALETTE` existente en vez de reemplazarla. El QSS hereda a todos los hijos y evita duplicar la definición de colores base.
- **Sí:** conservar el color de acento actual `rgb(42,130,218)` en lugar de introducir uno nuevo. Ya está validado en la spec 05 y da continuidad visual.
- **Sí:** tipografía Segoe UI, fuente nativa de Windows y referente del lenguaje Metro. La app corre en Windows, así que está garantizada sin empaquetar fuentes.
- **Sí:** limitar esta spec a re-skin (QSS + tipografía + colores + tiles) sin tocar layout ni navegación. Acota el riesgo; los ajustes de layout se evaluarán en una spec futura si hacen falta.
- **Sí:** dejar `QFileDialog`/`QMessageBox` con apariencia nativa. Estilarlos con QSS es frágil entre SO y son diálogos modales de uso puntual; no justifica el riesgo en esta spec.
- **No:** introducir tema claro ni toggle de tema. Sigue oscuro fijo hasta que exista un menú de opciones (spec futura).
- **No:** revivir la regla previa de "interfaz puramente funcional / sin estilo metro" (specs 04/05). El usuario la dio explícitamente por revertida; este es el punto donde el proyecto pasa a tener trabajo de diseño.

## Risks

| Risk | Mitigation |
|---|---|
| Un QSS global puede pisar la `DARK_PALETTE` y dejar algún widget con bajo contraste o ilegible. | El paso 4 del plan exige revisar visualmente cada widget de `OcrView` y ajustar el QSS ante cualquier bajo contraste antes de cerrar la spec. |
| Segoe UI no existe fuera de Windows; en otro SO el look metro se degradaría. | La app es de facto Windows-only; Qt hace fallback automático a una fuente sans-serif sin romper la app. Limitación conocida aceptada. |
| Los diálogos nativos, al quedar fuera del skin, pueden verse inconsistentes con el resto metro. | Decisión consciente; son modales de uso puntual, bajo impacto, se aborda en una spec futura si molesta. |
| Quitar `CHECKED_BUTTON_STYLE` de `sidebar_view.py` podría romper el resaltado del botón activo si el selector `QPushButton:checked` no se replica igual. | El paso 3 verifica manualmente que el tile activo siga resaltado por default tras mover el estilo al módulo centralizado. |
