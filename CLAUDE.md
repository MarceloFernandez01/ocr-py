# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Alcance del proyecto

MVP de un aplicativo de escritorio en Python para OCR (Optical Character Recognition): transcribe imágenes a texto en español e inglés, reconociendo la mayor cantidad de fuentes posible.

Restricciones del proyecto y decisiones técnicas cerradas en `specs/01-mvp-ocr-tesseract-tkinter.md`:

- **Evitar módulos externos salvo que sea estrictamente necesario.** Las dependencias externas aprobadas son `pytesseract` (motor OCR), `Pillow` (decodificación de imágenes en cualquier formato para la vista previa en GUI), `numpy` y `opencv-python` (preprocesamiento de imagen para OCR sobre fondos complejos, ver `specs/03-preprocesamiento-ocr.md`), `PySide6` (toolkit de GUI, ver `specs/04-migracion-pyside6-menu-inicio.md`), `argostranslate` (traducción offline del texto reconocido en OCR en vivo, ver `specs/11-traduccion-ocr-en-vivo.md`), `anthropic` (SDK oficial de Anthropic, motor OCR alternativo vía Claude Haiku 4.5, ver `specs/13-ocr-claude-motor-alternativo.md`) y `keyring` (almacenamiento seguro de la API key de Anthropic en el keyring del SO, ver `specs/13-ocr-claude-motor-alternativo.md`). No agregar otras sin pasar antes por una spec.
- **Respetar el patrón MVC** (Modelo-Vista-Controlador) en la organización del código: `model/` (lógica de OCR y config, sin importar PySide6), `view/` (ventana y widgets PySide6, sin llamar a `pytesseract` directamente), `controller/` (conecta eventos de la vista con el modelo).
- **GUI en PySide6 con skin visual estilo Metro** (tipografía Segoe UI, superficies planas, tiles, acento azul), centralizado en `view/metro_style.py` (ver `specs/06-reskin-metro.md`). Soporta tema oscuro y claro con toggle en caliente desde la vista de Configuración (ver `specs/07-menu-configuracion-sidebar.md`); default oscuro, persistido en `config.json`.
- **Motor OCR: Tesseract vía `pytesseract`.** El usuario debe instalar Tesseract-OCR manualmente en el sistema (no se instala vía pip ni se instala automáticamente desde la app). La app detecta la ruta por PATH; si no la encuentra, pide la ruta manualmente y la persiste en `config.json`.
- **Selector de idioma con 3 opciones fijas:** Español (`spa`), Inglés (`eng`), Ambos (`spa+eng`). Idiomas adicionales quedan para specs futuras.
- **Fuera de alcance del MVP:** guardado del texto a archivo o historial entre sesiones, instalación automática de Tesseract, motor ICR. (OCR en vivo/captura de pantalla ya está implementado, ver specs 08-10.)
- **El código debe estar documentado.** Cada módulo, clase y función pública lleva un docstring explicando su propósito (qué hace, parámetros y valor de retorno cuando no sean obvios). Esto tiene prioridad sobre la preferencia global de evitar comentarios/documentación innecesaria.
- **La IA no puede cambiar ni implementar nuevas funcionalidades si no se pide explisitamente.**  Solamente podra ser sugerencias, las cuales el usuario puede aprobar o rechazar.

El MVP descrito en `specs/01-mvp-ocr-tesseract-tkinter.md` ya está implementado. Estructura actual del código (detalle de cada módulo en su propio docstring):

- `main.py` — entry point, arranca `QApplication` + `MainWindow`.
- `model/config_model.py` — carga/guarda `config.json` (`tesseract_path`, `theme`).
- `model/tesseract_locator.py` — resuelve la ruta de Tesseract (PATH o config).
- `model/ocr_model.py` — wrapper de `pytesseract`, orquesta tiling y preprocesamiento.
- `model/image_tiling.py` — tiling/downscale de imágenes grandes (spec 02).
- `model/image_preprocessing.py` — variantes de preprocesamiento y upscaling con selección por confianza (spec 03).
- `model/image_diff.py` — compara capturas de pantalla para detectar cambios significativos, usado en el polling de OCR en vivo (spec 08).
- `model/translation_model.py` — traducción offline del texto reconocido vía `argostranslate`, con descarga on-demand del modelo de idioma (spec 11).
- `model/claude_ocr_model.py` — OCR alternativo vía Claude Haiku 4.5 (SDK `anthropic`), con import perezoso del SDK; redimensiona la imagen solo si excede los límites de tamaño de la API (spec 13); `transcribe_image_claude` devuelve `(texto, input_tokens, output_tokens)` para el cálculo de costo (spec 16).
- `model/text_diff.py` — compara dos transcripciones por umbral de similitud (`difflib.SequenceMatcher`, biblioteca estándar) para detectar cambio real de texto entre capturas en OCR en vivo, filtrando jitter/ruido visual (spec 16).
- `model/claude_usage_model.py` — costo por llamada a Claude Haiku 4.5 a partir de los tokens reales de la API y acumulación del gasto mensual en `config.json` (spec 16).
- `view/main_window.py` — `MainWindow`, sidebar + `QStackedWidget` con 3 vistas (`OcrView`, `LiveOcrView`, `SettingsView`) y una barra de gasto de Claude (`SpendMeterView`) debajo, visible solo con motor Claude y API key guardada; `apply_theme(theme)` para tema en caliente y `refresh_spend_meter()` para refrescar/ajustar el alto fijo de la ventana según esa barra (spec 16).
- `view/sidebar_view.py` — panel lateral persistente ("OCR de imágenes", "OCR en vivo", engranaje Configuración), señales `ocr_selected`/`live_ocr_selected`/`settings_selected`.
- `view/ocr_view.py` — flujo de OCR sobre imágenes (abrir, idioma, recorte/zoom/paneo sobre la preview, transcribir, resultado), soporta motor Tesseract o Claude según Configuración (specs 10, 12, 13).
- `view/live_ocr_view.py` — pantalla de OCR en vivo: activa el overlay de captura y controla el inicio/fin de la transcripción por polling (specs 08-09).
- `view/screen_overlay.py` — overlay flotante para seleccionar el segmento de pantalla a capturar en OCR en vivo.
- `view/settings_view.py` — vista de Configuración: `ThemeSwitch` (tema claro/oscuro en caliente), combo de motor OCR (Tesseract / Claude Haiku) con campo de API key enmascarado guardado en el keyring del SO, aviso de costo del motor Claude (spec 13), deslizadores de sensibilidad al cambio de texto/imagen en OCR en vivo (siempre visibles) e interruptor + cooldown + presupuesto mensual exclusivos del motor Claude (spec 16).
- `view/spend_meter_view.py` — `SpendMeterView`, franja horizontal con el progreso de gasto de Claude del mes en curso (llamadas, monto, presupuesto) y estado de alerta visual; solo presentación, sin lógica de negocio (spec 16).
- `view/metro_style.py` — única fuente del QSS estilo Metro (`get_stylesheet(theme)`), sin lógica de negocio.
- `view/assets/` — íconos de chevron para `QComboBox`, uno por tema.
- `controller/common.py` — utilidades compartidas entre `OcrController` y `LiveOcrController`: mapa de idiomas, prompt de ruta de Tesseract, label de progreso, constantes del keyring de la API key de Anthropic y `format_claude_error` (traduce excepciones del SDK `anthropic` a mensajes en español, spec 16).
- `controller/ocr_controller.py` — conecta `OcrView` con el Model: errores vía `QMessageBox`/`QFileDialog`, threading (`QThreadPool`/`QRunnable`) con contador de segundos, estado de recorte `_crop_box` (mapea preview→imagen original antes de transcribir) y despacho a Tesseract o Claude según el motor configurado; con Claude, registra el gasto (`register_call`) y refresca la barra de `MainWindow` (spec 16).
- `controller/live_ocr_controller.py` — ciclo de OCR en vivo: captura de pantalla, diff de píxeles (`image_diff`) y transcripción con Tesseract como detector de cambio de texto (`text_diff.has_text_changed`) antes de refrescar la vista o re-disparar traducción; con motor Claude y el interruptor `live_claude_enabled` activado, un cambio de texto real dispara `transcribe_image_claude` (respetando un cooldown configurable con cola de la captura más reciente) y el panel solo muestra resultados de Claude, nunca de Tesseract (spec 16).
- `controller/settings_controller.py` — conecta el toggle de tema, el selector de motor OCR y los controles de OCR en vivo (interruptor de Claude, sensibilidad de texto/píxeles, cooldown, presupuesto mensual) de `SettingsView` con el model (`save_theme()`, `config.json`, keyring) y con `MainWindow.apply_theme()`/`refresh_spend_meter()`.
- `requirements.txt` — `pytesseract`, `Pillow`, `numpy`, `opencv-python`, `PySide6`, `argostranslate`, `anthropic`, `keyring`.
- `config.json` — generado en runtime (no versionado, `.gitignore`), incluye `tesseract_path`, `theme`, `engine`, `min_word_confidence`, `live_claude_enabled`, `text_similarity_threshold`, `pixel_change_sensitivity`, `claude_cooldown_seconds`, `claude_monthly_budget_usd` y `claude_spend` (acumulador mensual `{month, usd, calls}`). La API key de Anthropic no se guarda acá, se guarda en el keyring del SO.
- `docs/fixes-ocr.md` — changelog acumulativo de correcciones menores al motor Tesseract (sin trade-off para el usuario, sin spec propia), generado por la skill `/tesseract-bug`.

No hay comandos de build/lint/test configurados en el repo (no hay `pyproject.toml` ni `Makefile`). Para correr la app: `python main.py`. Antes de asumir que existe un comando de test o lint, verificar con `ls`.

## Flujo de trabajo: specs

Este repositorio usa el flujo de trabajo basado en specs (skills `spec` y `spec-impl`, instaladas vía `.agents/skills/`, catálogo `Klerith/fernando-skills`):

- `/spec <descripción>` — diseña una spec nueva sección por sección, haciendo preguntas de clarificación antes de proponer estructura. Guarda el resultado en `specs/NN-slug.md` con estado `Draft`.
- `/spec-impl <NN-slug>` — implementa una spec ya marcada como `Approved` por el usuario. Crea (o reutiliza) una rama `spec-NN-slug`, muestra el resumen de la spec y avanza paso a paso, pausando después de cada paso del plan de implementación para revisión de diff.
- `/tesseract-bug <descripción>` — skill de proyecto (`.claude/skills/tesseract-bug/`) para reportar fallos de reconocimiento del motor Tesseract, con imagen adjunta o ruta cuando sea posible. Diagnostica contra el pipeline real (`model/ocr_model.py`, `model/image_preprocessing.py`, `model/image_tiling.py`) y decide por el trade-off del arreglo: si nadie pierde nada, aplica un fix acotado en una rama `fix-ocr-<slug>` y lo documenta en `docs/fixes-ocr.md`; si el arreglo sacrifica otro caso de uso, redacta ella misma una spec nueva sección por sección (mismo método que `/spec`) en `specs/NN-slug.md` con estado `Draft`. Solo cubre el motor Tesseract, nunca edita en `master`/`main`, y nunca hace commit/merge/push.

Reglas clave de este flujo:

- Nunca se escribe código durante `/spec` — esa skill solo produce el archivo `.md` de la spec.
- `/spec-impl` se niega a avanzar si el estado de la spec no significa "Approved" (en cualquier idioma).
- La creación automática de rama está controlada por `AutoCreateBranch` en `specs/.spec-config.yml` (por defecto `true`).
- `/tesseract-bug` siempre trabaja en una rama propia (`fix-ocr-<slug>`) que ella misma crea tras confirmación explícita; nunca edita código en `master` ni `main`.

Cuando se implemente una feature de este proyecto, sigue este flujo en vez de escribir código directamente salvo que el usuario pida explícitamente saltarlo.

**Specs existentes:**

- `specs/01-mvp-ocr-tesseract-tkinter.md` (`Implementado`) — MVP de la app de escritorio OCR descrita arriba.
- `specs/02-ocr-imagenes-grandes.md` (`Implementado`) — tiling y downscale para imágenes grandes, threading con contador de segundos.
- `specs/03-preprocesamiento-ocr.md` (`Implementado`) — preprocesamiento multi-variante (`numpy`/`opencv-python`) con selección por confianza y upscaling de imágenes chicas, para OCR sobre fondos complejos.
- `specs/04-migracion-pyside6-menu-inicio.md` (`Implementado`) — migración de la GUI de Tkinter a PySide6, con pantalla de inicio (menú de opciones) y tema oscuro fijo.
- `specs/05-menu-lateral-persistente.md` (`Implementado`) — menú lateral (sidebar) persistente en reemplazo de la pantalla de inicio, con `OcrView` activo por default y tamaño de ventana fijo.
- `specs/06-reskin-metro.md` (`Implementado`) — re-skin visual estilo Metro (Segoe UI, superficies planas, tiles, acento azul) vía `view/metro_style.py`, sin cambios de layout ni funcionales.
- `specs/07-menu-configuracion-sidebar.md` (`Implementado`) — botón de engranaje en el sidebar, vista `SettingsView` con toggle de tema claro/oscuro en caliente (persistido en `config.json`) y placeholder deshabilitado de motor OCR.
- `specs/08-ocr-en-vivo.md` (`Aprobado`) — OCR en vivo: overlay para seleccionar segmento de pantalla, captura periódica, diff de imágenes y transcripción automática ante cambios.
- `specs/09-live-ocr-boton-iniciar-transcripcion.md` (`Implementado`) — separa activar el overlay de iniciar la transcripción en OCR en vivo, y agrega labels de idioma.
- `specs/10-recorte-region-ocr-imagenes.md` (`Implementado`) — recorte de región sobre la imagen antes de transcribir en OCR de imágenes ("Activar recorte"/"Quitar recorte").
- `specs/11-traduccion-ocr-en-vivo.md` (`Aprobado`) — traducción offline (vía `argostranslate`) del texto reconocido en OCR en vivo, con selectores de idioma origen/destino y botón toggle sincronizado con el polling.
- `specs/12-zoom-paneo-ocr-imagenes.md` (`Implementado`) — zoom con rueda del mouse (centrado en el cursor) y paneo con click derecho en la preview de `OcrView`; simplifica el recorte de spec 10 a selección directa por click izquierdo.
- `specs/13-ocr-claude-motor-alternativo.md` (`Aprobado`) — motor OCR alternativo vía Claude Haiku 4.5 (SDK `anthropic`), seleccionable desde Configuración, con la API key guardada en el keyring del SO; la exclusión original de OCR en vivo la levanta `specs/16-filtro-cambio-texto-ocr-vivo.md`.
- `specs/16-filtro-cambio-texto-ocr-vivo.md` (`Aprobado`) — filtro de cambio de texto (`model/text_diff.py`) como cascada previa a refrescar la vista o llamar a la API en OCR en vivo; habilita Claude Haiku como motor de OCR en vivo detrás de ese filtro y un cooldown configurable, con medidor de consumo (`model/claude_usage_model.py`, `view/spend_meter_view.py`) en la barra inferior de la aplicación.
