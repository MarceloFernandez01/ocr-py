# Spec 14: Corrección de confusión I/pipe en Tesseract OCR

**Estado:** Implementado
**Dependencias:** `specs/03-preprocesamiento-ocr.md` (introduce `transcribe_image_variants`, punto único de cambio)
**Fecha:** 2026-07-25

**Objetivo:** Corregir que Tesseract transcriba la letra mayúscula "I" como el carácter pipe "|", bloqueando "|" en la configuración de Tesseract dentro de `transcribe_image_variants`, beneficiando tanto a OCR en vivo como a OCR de imágenes estático.

## Alcance

**Dentro del alcance:**

- Modificar `transcribe_image_variants` en `model/ocr_model.py`, agregando `config="-c tessedit_char_blacklist=|"` tanto a la llamada de `pytesseract.image_to_data` (usada para puntuar la confianza de cada variante) como a la llamada final de `pytesseract.image_to_string`.
- El fix beneficia automáticamente a las tres funciones públicas de `ocr_model.py` (`transcribe_large_image`, `transcribe_cropped_image`, `transcribe_image_variants`), ya que las tres delegan la transcripción por tile en `transcribe_image_variants`. Esto cubre tanto OCR en vivo como OCR de imágenes estático (con o sin tiling, con o sin recorte).

**Fuera del alcance:**

- Corrección de otras confusiones de caracteres similares (l minúscula, 1, etc.) — se acota estrictamente al caso "I" vs "|" confirmado en la captura del bug.
- Corrección de texto post-OCR (heurísticas de reemplazo sobre el resultado ya transcripto) — se descarta a favor de la configuración de Tesseract, según lo decidido.
- Cualquier configuración adicional de Tesseract (PSM, OEM, whitelist de caracteres) más allá del blacklist de "|".
- Hacer el blacklist configurable u opcional desde la GUI — queda fijo en el código.
- Reconocimiento de pipe "|" real en la imagen (ej. tablas con separadores, código): queda permanentemente deshabilitado como trade-off aceptado.

## Modelo de datos

No introduce estructuras nuevas ni cambia `config.json`. Es un cambio de una línea de configuración pasada a llamadas ya existentes de `pytesseract` dentro de `model/ocr_model.py`.

## Plan de implementación

1. **`model/ocr_model.py`: agregar blacklist de "|" a `transcribe_image_variants`.** Definir `tesseract_config = "-c tessedit_char_blacklist=|"` al inicio de la función y pasarlo como `config=tesseract_config` tanto en la llamada a `pytesseract.image_to_data` (dentro del loop de scoring por variante) como en la llamada final a `pytesseract.image_to_string`. Es el único paso del plan: no requiere pasos intermedios porque es un cambio acotado a una función ya existente, sin nuevos módulos ni dependencias.
   Prueba manual: correr `python main.py`, ir a OCR en vivo, capturar la misma imagen del bug reportado ("The moment I say it, I feel their gaze on me.") y confirmar que la transcripción ya no muestra "|" en lugar de "I". Repetir en OCR de imágenes estático con la misma imagen (guardada como archivo) y confirmar el mismo resultado. Transcribir además una imagen con texto normal ya usada antes (sin "I") y confirmar que no hay regresión.

## Criterios de aceptación

- [x] `transcribe_image_variants` en `model/ocr_model.py` pasa `config="-c tessedit_char_blacklist=|"` tanto a `pytesseract.image_to_data` como a `pytesseract.image_to_string`.
- [x] Al transcribir la imagen del bug reportado ("The moment I say it, I feel their gaze on me.") desde OCR en vivo, el resultado ya no contiene "|" en lugar de "I".
- [x] El mismo resultado correcto se obtiene al transcribir la misma imagen (como archivo) desde OCR de imágenes estático, con y sin recorte de región.
- [x] Una imagen con texto normal ya transcripta correctamente antes de este fix sigue transcribiéndose igual (sin regresión).
- [x] La app nunca vuelve a reconocer el carácter "|" literal en ninguna imagen (trade-off aceptado, verificable con una imagen de prueba que contenga un pipe real, donde ahora debería aparecer una "I" o "l" en su lugar en vez de "|").
- [x] No se modifica ningún otro archivo del proyecto; el cambio queda acotado a `model/ocr_model.py`.

## Decisions

- **Sí:** ajustar la configuración de Tesseract (`tessedit_char_blacklist=|`) en vez de aplicar una heurística de corrección de texto post-OCR. Es más simple, no depende de detectar patrones de texto ambiguos (¿cuándo un "|" aislado es realmente una "I" mal leída y cuándo no?), y deja que el propio clasificador de Tesseract resuelva la ambigüedad con su lógica de puntaje interna.
- **Sí:** aplicar el cambio en `transcribe_image_variants`, el punto único ya usado por OCR en vivo, OCR de imágenes grandes con tiling y OCR con recorte de región. Evita duplicar la configuración en tres lugares y garantiza que las tres funciones queden corregidas con un solo cambio.
- **Sí:** aceptar que la app nunca vuelva a reconocer un pipe "|" real en ninguna imagen. El caso de uso principal es texto en pantalla/imágenes (no código ni tablas con separadores), donde la confusión I/pipe es mucho más frecuente y molesta que la necesidad real de reconocer un pipe literal.
- **No:** acotar el fix solo a caracteres I/l/1 combinados. Se limita estrictamente al caso confirmado (I vs pipe); ampliar la cobertura de caracteres ambiguos queda para una spec futura si se detecta como problema recurrente.
- **No:** hacer el blacklist configurable desde la GUI. Es una corrección fija de comportamiento, no una preferencia que el usuario deba decidir.

## Identified risks

| Riesgo | Mitigación |
|---|---|
| Con ciertas fuentes o tamaños de texto, el clasificador de Tesseract podría elegir "l" minúscula en vez de "I" mayúscula al descartar "|", introduciendo un nuevo tipo de error de reconocimiento. | Se acepta como límite conocido: es preferible a la confusión actual con "|", que es visualmente más disruptiva. Si se vuelve recurrente, evaluar cobertura ampliada (I/l/1) en spec futura, ya descartada en el alcance de esta spec. |
| Una imagen que sí contenga un pipe real (código, tabla, log) ya no lo transcribirá correctamente nunca más. | Trade-off aceptado explícitamente por el usuario; el caso de uso principal de la app es texto corrido en pantalla/imágenes, donde esto es infrecuente. |
| El blacklist podría no eliminar el 100% de los casos si Tesseract, en variantes de preprocesamiento muy degradadas, sigue prefiriendo la forma de "|" por sobre cualquier alternativa disponible en su diccionario de glifos. | El criterio de aceptación pide verificación manual explícita con la imagen del bug reportado; si persistiera algún caso residual, se evaluaría en una spec de seguimiento. |
