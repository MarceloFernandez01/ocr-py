# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Alcance del proyecto

MVP de un aplicativo de escritorio en Python para OCR (Optical Character Recognition): transcribe imágenes a texto en español e inglés, reconociendo la mayor cantidad de fuentes posible.

Restricciones del proyecto (definidas en `readme.md`) y decisiones técnicas cerradas en `specs/01-mvp-ocr-tesseract-tkinter.md`:

- **Evitar módulos externos salvo que sea estrictamente necesario.** Las dependencias externas aprobadas son `pytesseract` (motor OCR), `Pillow` (decodificación de imágenes en cualquier formato para la vista previa en GUI), `numpy` y `opencv-python` (preprocesamiento de imagen para OCR sobre fondos complejos, ver `specs/03-preprocesamiento-ocr.md`), `PySide6` (toolkit de GUI, ver `specs/04-migracion-pyside6-menu-inicio.md`) y `argostranslate` (traducción offline del texto reconocido en OCR en vivo, ver `specs/11-traduccion-ocr-en-vivo.md`). No agregar otras sin pasar antes por una spec.
- **Respetar el patrón MVC** (Modelo-Vista-Controlador) en la organización del código: `model/` (lógica de OCR y config, sin importar PySide6), `view/` (ventana y widgets PySide6, sin llamar a `pytesseract` directamente), `controller/` (conecta eventos de la vista con el modelo).
- **GUI en PySide6 con skin visual estilo Metro** (tipografía Segoe UI, superficies planas, tiles, acento azul), centralizado en `view/metro_style.py` (ver `specs/06-reskin-metro.md`). Soporta tema oscuro y claro con toggle en caliente desde la vista de Configuración (ver `specs/07-menu-configuracion-sidebar.md`); default oscuro, persistido en `config.json`.
- **Motor OCR: Tesseract vía `pytesseract`.** El usuario debe instalar Tesseract-OCR manualmente en el sistema (no se instala vía pip ni se instala automáticamente desde la app). La app detecta la ruta por PATH; si no la encuentra, pide la ruta manualmente y la persiste en `config.json`.
- **Selector de idioma con 3 opciones fijas:** Español (`spa`), Inglés (`eng`), Ambos (`spa+eng`). Idiomas adicionales quedan para specs futuras.
- **Fuera de alcance del MVP:** guardado del texto a archivo o historial entre sesiones, instalación automática de Tesseract, motor ICR. (OCR en vivo/captura de pantalla ya está implementado, ver specs 08-10.)
- **El código debe estar documentado.** Cada módulo, clase y función pública lleva un docstring explicando su propósito (qué hace, parámetros y valor de retorno cuando no sean obvios). Esto tiene prioridad sobre la preferencia global de evitar comentarios/documentación innecesaria.

El MVP descrito en `specs/01-mvp-ocr-tesseract-tkinter.md` ya está implementado. Estructura actual del código (detalle de cada módulo en su propio docstring):

- `main.py` — entry point, arranca `QApplication` + `MainWindow`.
- `model/config_model.py` — carga/guarda `config.json` (`tesseract_path`, `theme`).
- `model/tesseract_locator.py` — resuelve la ruta de Tesseract (PATH o config).
- `model/ocr_model.py` — wrapper de `pytesseract`, orquesta tiling y preprocesamiento.
- `model/image_tiling.py` — tiling/downscale de imágenes grandes (spec 02).
- `model/image_preprocessing.py` — variantes de preprocesamiento y upscaling con selección por confianza (spec 03).
- `model/image_diff.py` — compara capturas de pantalla para detectar cambios significativos, usado en el polling de OCR en vivo (spec 08).
- `model/translation_model.py` — traducción offline del texto reconocido vía `argostranslate`, con descarga on-demand del modelo de idioma (spec 11).
- `view/main_window.py` — `MainWindow`, sidebar + `QStackedWidget` con 3 vistas (`OcrView`, `LiveOcrView`, `SettingsView`), tamaño fijo 1200x900, `apply_theme(theme)` para tema en caliente.
- `view/sidebar_view.py` — panel lateral persistente ("OCR de imágenes", "OCR en vivo", engranaje Configuración), señales `ocr_selected`/`live_ocr_selected`/`settings_selected`.
- `view/ocr_view.py` — flujo de OCR sobre imágenes (abrir, idioma, recorte de región opcional vía "Activar recorte"/"Quitar recorte", transcribir, preview, resultado) (spec 10).
- `view/live_ocr_view.py` — pantalla de OCR en vivo: activa el overlay de captura y controla el inicio/fin de la transcripción por polling (specs 08-09).
- `view/screen_overlay.py` — overlay flotante para seleccionar el segmento de pantalla a capturar en OCR en vivo.
- `view/settings_view.py` — vista de Configuración: `ThemeSwitch` (tema claro/oscuro en caliente) y combo deshabilitado de motor OCR.
- `view/metro_style.py` — única fuente del QSS estilo Metro (`get_stylesheet(theme)`), sin lógica de negocio.
- `view/assets/` — íconos de chevron para `QComboBox`, uno por tema.
- `controller/ocr_controller.py` — conecta `OcrView` con el Model: errores vía `QMessageBox`/`QFileDialog`, threading (`QThread`) con contador de segundos, y estado de recorte `_crop_box` (mapea preview→imagen original antes de transcribir).
- `controller/live_ocr_controller.py` — ciclo de OCR en vivo: captura de pantalla, diff (`image_diff`) para detectar cambios y disparo de transcripción por polling.
- `controller/settings_controller.py` — conecta el toggle de tema de `SettingsView` con `save_theme()` y `MainWindow.apply_theme()`.
- `requirements.txt` — `pytesseract`, `Pillow`, `numpy`, `opencv-python`, `PySide6`, `argostranslate`.
- `config.json` — generado en runtime (no versionado, `.gitignore`), incluye `tesseract_path` y `theme`.

No hay comandos de build/lint/test configurados en el repo (no hay `pyproject.toml` ni `Makefile`). Para correr la app: `python main.py`. Antes de asumir que existe un comando de test o lint, verificar con `ls`.

## Flujo de trabajo: specs

Este repositorio usa el flujo de trabajo basado en specs (skills `spec` y `spec-impl`, instaladas vía `.agents/skills/`, catálogo `Klerith/fernando-skills`):

- `/spec <descripción>` — diseña una spec nueva sección por sección, haciendo preguntas de clarificación antes de proponer estructura. Guarda el resultado en `specs/NN-slug.md` con estado `Draft`.
- `/spec-impl <NN-slug>` — implementa una spec ya marcada como `Approved` por el usuario. Crea (o reutiliza) una rama `spec-NN-slug`, muestra el resumen de la spec y avanza paso a paso, pausando después de cada paso del plan de implementación para revisión de diff.

Reglas clave de este flujo:

- Nunca se escribe código durante `/spec` — esa skill solo produce el archivo `.md` de la spec.
- `/spec-impl` se niega a avanzar si el estado de la spec no significa "Approved" (en cualquier idioma).
- La creación automática de rama está controlada por `AutoCreateBranch` en `specs/.spec-config.yml` (por defecto `true`).

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
