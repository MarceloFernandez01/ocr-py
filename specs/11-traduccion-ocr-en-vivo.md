# SPEC 11 — Traducción del texto reconocido en OCR en vivo

> **Status:** Aprobado
> **Depends on:** `specs/08-ocr-en-vivo.md`, `specs/09-live-ocr-boton-iniciar-transcripcion.md`
> **Date:** 2026-07-14
> **Objective:** Agregar traducción offline (vía `argostranslate`) del texto reconocido en OCR en vivo, con selectores de idioma origen/destino y un botón toggle que mantiene sincronizado un área de texto traducido con cada nueva transcripción.

## Scope

**In:**

- **`view/live_ocr_view.py`**: nueva segunda fila de controles debajo de la toolbar existente (combobox idioma OCR, "Activar selección", "Iniciar transcripción"). Incluye: `QLabel("Traducir desde")` + `source_language_combobox` (Español/Inglés), `QLabel("Traducir a")` + `target_language_combobox` (Español/Inglés), y `translation_button` (checkable, texto alterna "Activar traducción"/"Desactivar traducción", siempre habilitado). Cada control envuelto en `QVBoxLayout` con label arriba, siguiendo la convención de spec 09. Debajo del `QTextEdit` de resultado OCR existente se agrega un segundo `QTextEdit` de solo lectura para el texto traducido, con su propio `QLabel("Traducción")` encima. Señal `translate_toggled`. Setters: `set_translation_button_active(active: bool)`, `set_translated_text(text: str)`, `clear_translated_text()`.
- **`model/translation_model.py`** (nuevo): función pública `translate_text(text: str, source_lang: str, target_lang: str) -> str` que usa `argostranslate`. Mapea los códigos internos (`"spa"`/`"eng"`) a los códigos ISO de argos (`"es"`/`"en"`). Si el paquete de idioma para el par origen/destino no está instalado, lo busca en `argostranslate.package.get_available_packages()`, lo descarga e instala (`argostranslate.package.install_from_path`) antes de traducir. Si origen y destino coinciden, devuelve el texto sin llamar a argos (evita instalar/traducir un par idéntico).
- **`controller/live_ocr_controller.py`**: nuevo estado `self._translation_active: bool` y `self._translation_worker: TranslationWorker | None`. `on_translate_toggled()` alterna `_translation_active`; al activar, si ya hay texto reconocido, dispara una traducción inmediata. Mientras `_translation_active` es `True`, cada vez que el ciclo de polling/transcripción entrega un nuevo texto reconocido, se dispara automáticamente una traducción del texto nuevo (cancela/ignora resultado de una traducción anterior si todavía está corriendo). Al desactivar, no se limpia el texto traducido ya mostrado, solo deja de re-traducir.
- **`controller/live_ocr_controller.py`**: nueva clase `TranslationWorker(QThread)`, mismo patrón que `TranscriptionWorker` (spec 02): recibe `text`, `source_lang`, `target_lang`; en `run()` llama a `translate_text` y emite `finished(str)` o `error(str)`.
- **`view/metro_style.py`**: estilos para los nuevos `QComboBox`, `QLabel`, `translation_button` (reutilizando patrones ya definidos) y el nuevo `QTextEdit` de traducción, en ambos temas.
- **`requirements.txt`**: se agrega `argostranslate`.
- **`CLAUDE.md`**: se agrega `argostranslate` a la lista de dependencias externas aprobadas (con su propósito: traducción offline), se documenta `model/translation_model.py` en la estructura del proyecto, y se agrega la entrada de `specs/11-traduccion-ocr-en-vivo.md` al listado de specs existentes.

**Out (queda fuera de esta spec):**

- No se toca `OcrView` (OCR de imágenes) — la traducción queda limitada a `LiveOcrView`. Traducir imágenes estáticas queda para una spec futura si se pide.
- No se persiste `source_language`/`target_language` en `config.json` — son estado transitorio de la sesión, vuelven al default al reabrir la app o renavegar a "OCR en vivo".
- No se ofrecen más idiomas que Español/Inglés en los selectores de traducción, consistente con el selector de idioma de OCR existente.
- No se pre-descargan ni empaquetan los modelos de `argostranslate` en la instalación de la app — se descargan on-demand la primera vez que se necesita ese par de idiomas (requiere internet esa primera vez).
- El `QTextEdit` de traducción es de solo lectura, igual que el de resultado OCR — no se agrega edición manual del texto traducido.
- No se agrega caché de traducciones repetidas entre pares de idiomas ya usados en la sesión (cada traducción se recalcula).

## Data model

```python
# model/translation_model.py (nuevo)

LANGUAGE_CODE_MAP = {
    "spa": "es",
    "eng": "en",
}
"""Mapea los códigos internos de idioma (los mismos que usa `model/ocr_model.py`
para Tesseract) a los códigos ISO de dos letras que espera `argostranslate`."""


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Traduce `text` de `source_lang` a `target_lang` (códigos internos "spa"/"eng").
    Si `source_lang == target_lang`, devuelve `text` sin modificar. Si el
    paquete de idioma para el par origen/destino no está instalado, lo busca
    en `argostranslate.package.get_available_packages()`, lo descarga
    (`argostranslate.package.install_from_path`) y recién entonces traduce."""
```

```python
# controller/live_ocr_controller.py (ampliación)

class TranslationWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        parent: QObject | None = None,
    ) -> None:
        """Corre `translate_text` en un hilo aparte. Mismo patrón que
        `TranscriptionWorker`: `run()` llama al model y emite `finished(str)`
        con el resultado o `error(str)` si `translate_text` levanta una
        excepción (ej. sin internet en la primera descarga del modelo)."""


class LiveOcrController(QObject):
    # Nuevo estado en memoria (no persistido):
    self._translation_active: bool  # arranca en False
    self._translation_worker: TranslationWorker | None  # None cuando no hay traducción en curso
```

```python
# view/live_ocr_view.py (ampliación)

# Señal nueva:
translate_toggled = Signal()

# Setters nuevos:
def set_translation_button_active(self, active: bool) -> None: ...
def set_translated_text(self, text: str) -> None: ...
def clear_translated_text(self) -> None: ...

# Controles nuevos expuestos como atributos:
self.source_language_combobox: QComboBox  # "Español" / "Inglés" -> "spa" / "eng"
self.target_language_combobox: QComboBox  # "Español" / "Inglés" -> "spa" / "eng"
self.translation_button: QPushButton      # checkable, alterna texto
self.translated_text_edit: QTextEdit      # solo lectura
```

No se agregan claves a `config.json`: igual que el recorte de spec 10, el estado de traducción (idiomas seleccionados, activo/inactivo) es transitorio de la sesión de OCR en vivo, no persistido.

## Implementation plan

1. **`requirements.txt` + `CLAUDE.md`: aprobar la dependencia.** Agregar `argostranslate` a `requirements.txt`. Actualizar `CLAUDE.md`: sumar `argostranslate` a la lista de dependencias externas aprobadas (con su propósito), documentar `model/translation_model.py` en la estructura del proyecto, y agregar la entrada `specs/11-traduccion-ocr-en-vivo.md` (estado `Aprobado`) al listado de specs existentes.
   Prueba manual: `pip install -r requirements.txt` no falla; `python -c "import argostranslate"` no explota.

2. **`model/translation_model.py`: `translate_text()`.** Implementar `LANGUAGE_CODE_MAP` y `translate_text(text, source_lang, target_lang)`: si `source_lang == target_lang`, retorna `text` sin tocar `argostranslate`; si no, resuelve el paquete instalado o lo descarga/instala vía `argostranslate.package` para el par de códigos ISO, y traduce con `argostranslate.translate.translate`.
   Prueba manual: `python -c "from model.translation_model import translate_text; print(translate_text('hello world', 'eng', 'spa'))"` descarga el modelo la primera vez (requiere internet) y devuelve el texto traducido; correrlo de nuevo no vuelve a descargar.

3. **`view/live_ocr_view.py`: segunda fila de controles + área de traducción.** Agregar `source_language_combobox` y `target_language_combobox` (cada uno con `QLabel` arriba, "Traducir desde"/"Traducir a", opciones Español/Inglés) y `translation_button` (checkable, texto inicial "Activar traducción", envuelto en `QVBoxLayout` con `QLabel("")` vacío arriba) en una nueva fila de toolbar debajo de la existente. Agregar `QLabel("Traducción")` + `translated_text_edit` (`QTextEdit`, `setReadOnly(True)`) debajo del `QTextEdit` de resultado OCR. Señal `translate_toggled` conectada al `clicked` de `translation_button`. Métodos `set_translation_button_active(active)`, `set_translated_text(text)`, `clear_translated_text()`.
   Prueba manual: instanciar `LiveOcrView` sola, confirmar que aparece la nueva fila alineada, el área de traducción vacía debajo del resultado OCR, y que los setters nuevos no explotan al llamarlos con datos de prueba.

4. **`view/metro_style.py`: estilos de los controles nuevos.** Agregar reglas para los dos `QComboBox` nuevos (reutilizando el estilo ya definido para `language_combobox`), `translation_button` (mismo patrón `:checked` que `transcription_button`), el `QLabel("Traducción")` (mismo estilo secundario que "Idioma") y `translated_text_edit` (mismo estilo que el `QTextEdit` de resultado OCR existente), en ambos temas.
   Prueba manual: alternar tema en Configuración, confirmar que los controles nuevos se ven legibles y consistentes en claro/oscuro.

5. **`controller/live_ocr_controller.py`: `TranslationWorker` y ciclo de traducción.** Implementar `TranslationWorker(QThread)` (recibe `text`/`source_lang`/`target_lang`, emite `finished(str)`/`error(str)`). Agregar `self._translation_active = False` y `self._translation_worker = None`. Conectar `translate_toggled` → `on_translate_toggled`: alterna `_translation_active`, actualiza `translation_button` vía `set_translation_button_active`; si pasa a `True` y ya existe texto reconocido, dispara una traducción inmediata (`_start_translation(texto_actual)`). En el callback que hoy recibe el resultado de cada transcripción del polling (`_on_transcription_finished` o equivalente), agregar: si `self._translation_active`, llamar a `_start_translation(nuevo_texto)`. `_start_translation(text)`: si ya hay un `TranslationWorker` corriendo, lo descarta (no bloquea, simplemente se ignora su resultado al llegar tarde vía un flag/id de secuencia); crea y arranca uno nuevo con `source_language_combobox`/`target_language_combobox` actuales; en `finished`, llama a `view.set_translated_text(resultado)`; en `error`, muestra `QMessageBox` de error sin detener el polling ni desactivar `_translation_active`. `stop()` (navegación afuera) también cancela cualquier `TranslationWorker` en curso, sin limpiar el texto ya mostrado.
   Prueba manual: activar transcripción en OCR en vivo, clickear "Activar traducción" y confirmar que aparece la traducción del texto actual; cambiar la captura (mover overlay a otro texto) y confirmar que la traducción se actualiza sola sin clickear nada más; clickear "Desactivar traducción" y confirmar que deja de actualizarse pero conserva el último texto traducido visible; simular una traducción sin modelo descargado y sin internet, confirmar que aparece el `QMessageBox` de error y el resto del flujo OCR sigue funcionando.

6. **Verificación end-to-end.** Recorrido manual completo: activar selección → iniciar transcripción → activar traducción → cambiar el área capturada varias veces confirmando que ambos textos (reconocido y traducido) se mantienen sincronizados → desactivar traducción → pausar/reanudar transcripción → cerrar overlay con X y confirmar que todo se resetea. Alternar tema y confirmar legibilidad de los controles nuevos. Confirmar que "OCR de imágenes" (specs 01-03, 10) sigue funcionando sin regresiones. Revisión de imports rotos.
   Prueba: recorrido manual + revisión de imports rotos.

## Acceptance criteria

- [ ] `LiveOcrView` muestra una segunda fila con "Traducir desde", "Traducir a" (ambos Español/Inglés) y el botón "Activar traducción", alineados entre sí, debajo de la fila existente.
- [ ] Debajo del resultado OCR aparece un área "Traducción" de solo lectura, vacía por default.
- [ ] El botón de traducción está siempre habilitado, incluso sin texto reconocido todavía.
- [ ] Clickear "Activar traducción" con texto reconocido ya visible traduce ese texto de inmediato y el botón pasa a "Desactivar traducción".
- [ ] Con la traducción activa, cada nueva transcripción disparada por el polling actualiza automáticamente el área de traducción, sin necesidad de volver a clickear el botón.
- [ ] Clickear "Desactivar traducción" detiene la actualización automática pero conserva visible el último texto traducido.
- [ ] Si origen y destino son el mismo idioma, la traducción no falla y devuelve el texto sin cambios.
- [ ] La primera traducción de un par de idiomas nuevo descarga el modelo de `argostranslate` automáticamente; traducciones posteriores del mismo par no vuelven a descargar.
- [ ] Si la descarga o traducción falla (ej. sin internet), se muestra un `QMessageBox` de error y el resto del flujo de OCR en vivo (captura, transcripción, polling) sigue funcionando sin interrupciones.
- [ ] La descarga/traducción corre en un `QThread` dedicado (`TranslationWorker`); la ventana no se congela mientras traduce.
- [ ] Cerrar el overlay con la X o navegar afuera de "OCR en vivo" cancela cualquier traducción en curso sin dejar hilos huérfanos.
- [ ] `OcrView` y el resto de "OCR de imágenes" (specs 01-03, 10) siguen funcionando sin regresiones.
- [ ] MVC respetado: `view/live_ocr_view.py` no importa `argostranslate` ni contiene lógica de traducción; `model/translation_model.py` no importa PySide6; el ciclo de activar/desactivar y disparar traducciones vive en `LiveOcrController`.
- [ ] Los controles nuevos son legibles y consistentes en ambos temas (claro/oscuro).
- [ ] `CLAUDE.md` refleja `argostranslate` como dependencia aprobada, documenta `model/translation_model.py` y lista `specs/11-traduccion-ocr-en-vivo.md`.

## Decisions

- **Sí:** `argostranslate` como motor de traducción offline, en vez de una API con key (Google Translate, DeepL, etc.). Coherente con el resto del proyecto (Tesseract local, sin dependencias de red obligatorias en el uso normal) y con el pedido explícito del usuario de no requerir API key.
- **Sí:** la traducción solo se agrega a `LiveOcrView`, no a `OcrView`. El caso de uso principal es texto en vivo (subtítulos, pantallas en otro idioma); traducir imágenes estáticas puede pedirse como spec futura si hace falta.
- **Sí:** botón separado "Activar/Desactivar traducción" en vez de traducir automáticamente sin que el usuario lo pida. Evita el costo de traducir (y potencialmente descargar un modelo) cuando el usuario solo quiere el texto reconocido.
- **Sí:** una vez activada, la traducción se re-dispara automáticamente en cada nueva transcripción del polling, en vez de requerir un click por cada actualización. El caso de uso típico de OCR en vivo es texto que cambia solo (subtítulos, pantallas dinámicas); forzar un click manual por cada cambio anularía el propósito de "en vivo".
- **Sí:** selector de idioma origen (`source_language_combobox`) independiente del idioma de reconocimiento OCR, en vez de inferirlo de este último. El idioma de OCR puede ser "Ambos" (`spa+eng`), ambiguo para elegir un origen de traducción; un selector explícito evita esa ambigüedad sin agregar heurísticas.
- **Sí:** si origen y destino coinciden, se llama igual a `translate_text` y esta devuelve el texto sin cambios (caso manejado dentro del model, sin lógica especial en el controller ni deshabilitar el botón). Mantiene el flujo simple y sin estados adicionales en la UI.
- **Sí:** descarga on-demand del modelo de `argostranslate` la primera vez que se necesita un par de idiomas, en vez de exigir instalación manual previa (a diferencia de Tesseract). A diferencia de Tesseract (binario del sistema, sin gestor de paquetes de Python), `argostranslate` expone su propio mecanismo de descarga de modelos vía pip, así que automatizarlo no rompe la restricción de "no instalar Tesseract automáticamente" (motor distinto, mecanismo distinto).
- **Sí:** `TranslationWorker(QThread)` dedicado, mismo patrón que `TranscriptionWorker`, en vez de traducir en el hilo principal. La descarga del modelo (primera vez) puede tardar varios segundos; bloquear la UI sería inconsistente con el resto del proyecto, que ya usa threading para operaciones lentas (spec 02).
- **Sí:** ante error de traducción (sin internet, fallo de descarga), se muestra `QMessageBox` inmediato y el resto del flujo de OCR en vivo sigue intacto, en vez de fallar silenciosamente o interrumpir el polling. Consistente con el manejo de errores ya usado en `OcrController`/`LiveOcrController` para otros fallos (ej. Tesseract no encontrado).
- **No:** persistir idiomas origen/destino ni estado activo/inactivo de traducción en `config.json`. Es estado transitorio de la sesión de OCR en vivo, sin necesidad planteada de recordarlo (mismo criterio que el recorte de spec 10).
- **No:** ofrecer más idiomas que Español/Inglés en los selectores de traducción. Mantiene consistencia con el único par que soporta hoy el reconocimiento OCR del proyecto.
- **No:** cachear traducciones repetidas dentro de la sesión. No es un problema real de performance para el volumen de texto esperado (fragmentos cortos de pantalla), y agregar caché sería complejidad no pedida.
- **Sí:** actualizar `CLAUDE.md` (lista de dependencias aprobadas, estructura de módulos, índice de specs) como parte del plan de implementación de esta spec, en vez de un cambio manual aparte. Sigue el precedente de spec 04, que documentó la migración a PySide6 en el mismo flujo.
- **Sí:** por defecto, las pruebas manuales de cada paso del plan de implementación las ejecuta el usuario, no el asistente; el asistente solo verifica por otros medios (lectura de código, `grep`, chequeo de imports) cuando el usuario no pueda evaluar el cambio corriendo el proyecto. Mismo default heredado de specs 09 y 10.

## Risks

| Risk | Mitigation |
|---|---|
| La descarga del modelo de `argostranslate` (primera vez para un par de idiomas) requiere internet; si el usuario está offline, la traducción falla justo cuando más se necesita (ej. usando la app sin conexión). | El paso 5 cubre explícitamente ese caso: `QMessageBox` de error claro, el resto del flujo OCR en vivo sigue funcionando, y el usuario puede reintentar apenas tenga conexión sin reiniciar la app. |
| Si el usuario clickea "Activar traducción" y luego el polling dispara varias transcripciones nuevas en rápida sucesión (texto cambiando rápido en pantalla), pueden acumularse varios `TranslationWorker` corriendo en paralelo, con resultados que llegan fuera de orden y pisan el texto traducido con una versión vieja. | El paso 5 exige descartar/ignorar el resultado de un `TranslationWorker` anterior si ya se lanzó uno más nuevo (vía flag o id de secuencia), asegurando que `translated_text_edit` siempre refleje la traducción del texto reconocido más reciente. |
| `argostranslate` descarga y cachea modelos en el filesystem del usuario (fuera de `config.json`, en su directorio de datos de la librería); esto es un efecto colateral no versionado por la app que puede sorprender en discos con poco espacio. | Es un comportamiento estándar y documentado de `argostranslate`, fuera del control de esta spec; se acepta como parte de usar la librería tal cual, sin agregar gestión de espacio en disco (fuera de alcance). |
| Cerrar el overlay o navegar afuera de "OCR en vivo" mientras un `TranslationWorker` está corriendo podría dejar un hilo huérfano o intentar actualizar una vista ya destruida. | El paso 5 exige que `stop()` cancele/desconecte cualquier `TranslationWorker` en curso, mismo patrón ya usado para `TranscriptionWorker`/polling en `stop()` existente (specs 08-09). |
