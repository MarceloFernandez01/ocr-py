# Spec 15: Filtro de confianza por palabra en el texto OCR

**Estado:** Aprobado
**Dependencias:** `specs/03-preprocesamiento-ocr.md` (introduce `transcribe_image_variants`, punto único a modificar), `specs/07-menu-configuracion-sidebar.md` (vista de Configuración donde se agrega el control)
**Fecha:** 2026-08-17

**Objetivo:** Descartar del texto final de Tesseract las palabras reconocidas con confianza por debajo de un umbral configurable desde Configuración, para eliminar ruido gráfico (íconos, bordes, artefactos) que hoy se cuela sin filtro en `transcribe_image_variants`.

## Alcance

**Dentro del alcance:**w

- Modificar `transcribe_image_variants` en `model/ocr_model.py` para que el texto final se reconstruya filtrando por confianza de palabra, en vez de usar `pytesseract.image_to_string` directo sobre toda la variante ganadora (línea 94 actual). Se reconstruye a partir de `image_to_data` sobre la variante ganadora, descartando las palabras con confianza por debajo del umbral configurado.
- El fix beneficia automáticamente a las tres funciones públicas de `ocr_model.py` (`transcribe_large_image`, `transcribe_cropped_image`, `transcribe_image_variants`), igual que la spec 14, cubriendo tanto OCR en vivo como OCR de imágenes estático.
- Nueva clave `min_word_confidence` en `config.json`, con valor por defecto (a confirmar en la sección de Modelo de datos).
- Nuevo control en `SettingsView` para ajustar el umbral, incluyendo la opción de desactivar el filtrado por completo.
- El umbral se lee en `OcrController` y `LiveOcrController` desde `config.json` y se pasa a `transcribe_image_variants`.

**Fuera del alcance:**

- Detección específica de patrones de ruido (tokens cortos no alfabéticos, íconos, bordes) — se descartó a favor de un umbral de confianza genérico, según lo decidido en la conversación.
- Ajuste automático o adaptativo del umbral según el contenido de la imagen — el umbral es un valor fijo que configura el usuario, no se calcula dinámicamente por imagen.
- Reordenamiento o reconstrucción de layout del texto filtrado más allá de lo que ya produce Tesseract (se preservan saltos de línea tal como los da `image_to_data`).
- Motor Claude Haiku — no usa este pipeline, queda fuera por completo (spec 13 es independiente).

## Modelo de datos

**`config.json`** — nueva clave `min_word_confidence`:

```json
{
  "tesseract_path": "...",
  "theme": "dark",
  "engine": "tesseract",
  "min_word_confidence": 30
}
```

- `min_word_confidence`: entero 0-100 (default `30`). Palabras que `pytesseract.image_to_data` reconoce con `conf < min_word_confidence` se descartan del texto final. `0` desactiva el filtro por completo (comportamiento idéntico al actual, sin regresión para quien lo baje a `0`).

**`model/ocr_model.py`** — cambios sobre lo existente:

- `transcribe_image_variants(image, language_code, tesseract_path, min_word_confidence: int = 0)`: gana el nuevo parámetro. La línea final (hoy `pytesseract.image_to_string(best_variant, ...)`) se reemplaza por una reconstrucción del texto a partir de `pytesseract.image_to_data(best_variant, ...)`, uniendo solo las palabras con `conf >= min_word_confidence`, preservando el agrupamiento por línea que ya reporta `image_to_data` (`data["line_num"]`/`data["block_num"]`).
- `transcribe_large_image` y `transcribe_cropped_image` ganan el mismo parámetro y lo propagan a cada llamada de `transcribe_image_variants` por tile.

**`model/config_model.py`** — nueva función `save_min_word_confidence(value: int)`, análoga a `save_theme()`/`save_engine()`.

**`view/settings_view.py`** — nuevo `QSpinBox` (rango 0-100) con label "Filtrar ruido (confianza mínima)", valor inicial desde `config.json`. Nueva señal `min_word_confidence_changed(int)`.

**`controller/settings_controller.py`** — conecta la nueva señal, persiste el valor vía `save_min_word_confidence()`.

**`controller/ocr_controller.py`** y **`controller/live_ocr_controller.py`** — leen `min_word_confidence` de `config.json` y lo pasan en cada llamada a `transcribe_large_image`/`transcribe_cropped_image`/`transcribe_image_variants`.

## Plan de implementación

1. **`model/ocr_model.py`: filtrado por confianza en `transcribe_image_variants`.** Agregar el parámetro `min_word_confidence: int = 0` a las tres funciones públicas y reemplazar la línea final `pytesseract.image_to_string(best_variant, ...)` por una reconstrucción del texto desde `pytesseract.image_to_data(best_variant, ...)`, descartando palabras con `conf < min_word_confidence` y preservando el agrupamiento por línea. El default `0` significa que, sin nadie pasando el parámetro todavía, el comportamiento es idéntico al actual.
   Prueba manual: correr `python main.py`, transcribir en OCR de imágenes y en OCR en vivo con casos ya probados antes; confirmar que el resultado es exactamente igual que hoy (nadie pasa `min_word_confidence` todavía, default `0`).

2. **`model/config_model.py`: persistencia de `min_word_confidence`.** Agregar la clave a la carga/guardado de `config.json` con default `30`, y `save_min_word_confidence(value: int)`.
   Prueba manual: borrar `config.json`, correr la app, confirmar que se regenera con `"min_word_confidence": 30`. Editar el valor a mano en el archivo, reiniciar la app, confirmar que se lee correctamente (sin UI todavía, solo el modelo).

3. **`view/settings_view.py`: control de UI (sin conectar lógica todavía).** Agregar `QSpinBox` (0-100) con label "Filtrar ruido (confianza mínima)", valor inicial leído de `config.json`, y la señal `min_word_confidence_changed(int)` — se emite pero nada la escucha aún.
   Prueba manual: ir a Configuración, confirmar que el nuevo campo aparece con el valor `30` cargado, y que cambiarlo no tiene efecto real todavía (no conectado). Confirmar que el resto de Configuración sigue funcionando igual.

4. **`controller/settings_controller.py`: conectar el control.** Conectar `min_word_confidence_changed` a `save_min_word_confidence()`.
   Prueba manual: cambiar el valor en Configuración, cerrar y reabrir la app, confirmar que el campo mantiene el nuevo valor (persistencia en `config.json`).

5. **`controller/ocr_controller.py` y `controller/live_ocr_controller.py`: usar el umbral al transcribir con Tesseract.** Leer `min_word_confidence` de `config.json` y pasarlo en cada llamada a `transcribe_large_image`/`transcribe_cropped_image`/`transcribe_image_variants`.
   Prueba manual: con el umbral en `30` (default), reproducir el caso reportado (botón "Change Outfit" en OCR en vivo) y confirmar que el resultado ya no incluye `= =` ni `o` sueltos, solo "Change Outfit". Repetir en OCR de imágenes estático con la misma imagen guardada como archivo. Transcribir además una imagen de texto normal ya reconocida bien antes de este cambio y confirmar que no hay regresión. Bajar el umbral a `0` desde Configuración y confirmar que vuelve el comportamiento original (validación del mecanismo de desactivación).

## Criterios de aceptación

- [ ] `config.json` incluye la clave `min_word_confidence` (entero 0-100, default `30`); un `config.json` sin esa clave se migra al abrir la app sin romper `tesseract_path`/`theme`/`engine` existentes.
- [ ] `transcribe_image_variants`, `transcribe_large_image` y `transcribe_cropped_image` en `model/ocr_model.py` aceptan `min_word_confidence` y descartan del texto final las palabras con `conf` por debajo del umbral.
- [ ] Con `min_word_confidence` en `0`, el resultado de cualquier transcripción es idéntico al comportamiento previo a esta spec (sin regresión, filtro desactivado).
- [ ] Con el umbral en `30` (default), transcribir el botón "Change Outfit" reportado en el bug (desde OCR en vivo) ya no muestra `= =` ni `o` sueltos; el resultado es únicamente "Change Outfit".
- [ ] El mismo resultado correcto se obtiene al transcribir la misma imagen (como archivo) desde OCR de imágenes estático, con y sin recorte de región.
- [ ] Una imagen con texto normal ya transcripta correctamente antes de este fix sigue transcribiéndose igual con el umbral default (`30`).
- [ ] La vista de Configuración muestra un control para ajustar `min_word_confidence` (0-100), con el valor persistido en `config.json` tras cerrar y reabrir la app.
- [ ] El motor Claude Haiku (spec 13) no se ve afectado por este cambio; sigue sin usar `image_preprocessing.py` ni `ocr_model.py`.
- [ ] No se modifican otros archivos fuera de `model/ocr_model.py`, `model/config_model.py`, `view/settings_view.py`, `controller/settings_controller.py`, `controller/ocr_controller.py` y `controller/live_ocr_controller.py`.

## Decisions

- **Sí:** umbral de confianza genérico por palabra, en vez de una detección específica de patrones de ruido (tokens cortos no alfabéticos como "=", "o"). Es más simple de implementar y cubre este caso y otros análogos (ruido de fondo, artefactos de compresión, otros íconos), según lo decidido en la conversación.
- **Sí:** el umbral queda configurable desde Configuración, a diferencia del blacklist fijo de la spec 14. Es la forma de mitigar el trade-off del filtrado genérico: si el usuario nota pérdida de texto real de baja confianza (fuentes decorativas, texto pequeño), puede bajar el umbral o desactivarlo (`0`) sin esperar un cambio de código.
- **Sí:** valor por defecto `30` (no `0`). Un default de `0` no resolvería el bug reportado sin que el usuario descubra y ajuste el control manualmente; `30` es lo bastante bajo para no filtrar texto legítimo de confianza media, y lo bastante alto para descartar el ruido gráfico observado en el caso reportado.
- **Sí:** reconstruir el texto final desde `pytesseract.image_to_data` (que ya calcula `conf` por palabra) en vez de post-procesar el string final de `image_to_string` con heurísticas de texto. Reutiliza información que Tesseract ya provee, sin adivinar qué es ruido a partir del texto ya ensamblado.
- **Sí:** aplicar el cambio en `transcribe_image_variants`, punto único ya usado por OCR en vivo y OCR de imágenes estático (con tiling y con recorte), igual que la spec 14. Evita duplicar lógica.
- **No:** detección específica de patrones de ruido (tokens cortos, símbolos sueltos). Descartada a favor del umbral genérico por decisión explícita en la conversación.
- **No:** ajuste automático o adaptativo del umbral según el contenido de cada imagen. Queda como valor fijo que ajusta el usuario manualmente; una heurística adaptativa es complejidad no pedida.

## Identified risks

| Riesgo | Mitigación |
|---|---|
| El umbral default (`30`) podría filtrar texto real de confianza media-baja (fuentes decorativas, contornos gruesos, texto pequeño), degradando casos que hoy funcionan bien. | Trade-off aceptado explícitamente y mitigado con el control configurable en Configuración: si el usuario detecta pérdida de texto real, puede bajar el umbral o desactivarlo (`0`) sin necesidad de un nuevo fix de código. |
| El umbral default (`30`) podría no ser suficiente para descartar ruido gráfico más "confiado" que el caso reportado (íconos que Tesseract reconoce con confianza media-alta como texto). | El criterio de aceptación exige verificación manual con la imagen del bug reportado; si persistiera ruido residual con casos análogos, se evaluaría un ajuste de default o una spec de seguimiento. |
| Reconstruir el texto desde `image_to_data` en vez de `image_to_string` podría alterar sutilmente el espaciado o los saltos de línea del resultado, incluso con el umbral en `0`. | El criterio de no regresión exige que, con umbral `0`, el resultado sea idéntico al actual; si la reconstrucción manual de líneas no reproduce el comportamiento exacto de `image_to_string`, se ajusta la agrupación por `line_num`/`block_num` hasta lograrlo antes de dar el paso 1 por cerrado. |
