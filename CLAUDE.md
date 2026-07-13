# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Alcance del proyecto

MVP de un aplicativo de escritorio en Python para OCR (Optical Character Recognition): transcribe imágenes a texto en español e inglés, reconociendo la mayor cantidad de fuentes posible.

Restricciones del proyecto (definidas en `readme.md`) y decisiones técnicas cerradas en `specs/01-mvp-ocr-tesseract-tkinter.md`:

- **Evitar módulos externos salvo que sea estrictamente necesario.** Las dependencias externas aprobadas son `pytesseract` (motor OCR), `Pillow` (decodificación de imágenes en cualquier formato para la vista previa en GUI), `numpy` y `opencv-python` (preprocesamiento de imagen para OCR sobre fondos complejos, ver `specs/03-preprocesamiento-ocr.md`) y `PySide6` (toolkit de GUI, ver `specs/04-migracion-pyside6-menu-inicio.md`). No agregar otras sin pasar antes por una spec.
- **Respetar el patrón MVC** (Modelo-Vista-Controlador) en la organización del código: `model/` (lógica de OCR y config, sin importar PySide6), `view/` (ventana y widgets PySide6, sin llamar a `pytesseract` directamente), `controller/` (conecta eventos de la vista con el modelo).
- **GUI sí está en alcance** (PySide6), pero **sin diseño pulido ni estilo "metro"** por ahora — interfaz puramente funcional. Tema oscuro fijo por default (sin toggle de UI todavía).
- **Motor OCR: Tesseract vía `pytesseract`.** El usuario debe instalar Tesseract-OCR manualmente en el sistema (no se instala vía pip ni se instala automáticamente desde la app). La app detecta la ruta por PATH; si no la encuentra, pide la ruta manualmente y la persiste en `config.json`.
- **Selector de idioma con 3 opciones fijas:** Español (`spa`), Inglés (`eng`), Ambos (`spa+eng`). Idiomas adicionales quedan para specs futuras.
- **Fuera de alcance del MVP:** OCR en vivo/captura de pantalla, guardado del texto a archivo o historial entre sesiones, instalación automática de Tesseract, motor ICR.
- **El código debe estar documentado.** Cada módulo, clase y función pública lleva un docstring explicando su propósito (qué hace, parámetros y valor de retorno cuando no sean obvios). Esto tiene prioridad sobre la preferencia global de evitar comentarios/documentación innecesaria.

El MVP descrito en `specs/01-mvp-ocr-tesseract-tkinter.md` ya está implementado. Estructura actual del código:

- `main.py` — punto de entrada; instancia `QApplication`, crea la `MainWindow` (PySide6) y corre `app.exec()`.
- `model/config_model.py` — `load_config()` / `save_tesseract_path()`, lee/escribe `config.json` (incluye clave `"theme"`, default `"dark"`).
- `model/tesseract_locator.py` — `resolve_tesseract_path()`, detecta Tesseract por PATH o por `config.json`.
- `model/ocr_model.py` — `transcribe(image_path, language_code, tesseract_path)`, envuelve `pytesseract`; orquesta tiling y preprocesamiento.
- `model/image_tiling.py` — divide/downscale imágenes grandes en tiles para OCR (spec 02).
- `model/image_preprocessing.py` — genera variantes de preprocesamiento (`numpy`/`opencv-python`) y upscaling de imágenes chicas, con selección por confianza (spec 03).
- `view/main_window.py` — `MainWindow` (`QMainWindow`), layout horizontal con `SidebarView` (ancho fijo 200px) a la izquierda y un `QStackedWidget` de contenido a la derecha con `OcrView` (índice 0, activo por default), tamaño fijo `setFixedSize(1200, 900)`, aplica tema oscuro fijo (spec 05).
- `view/sidebar_view.py` — `SidebarView`, panel lateral persistente con botón "OCR de imágenes" (checkable, resalta la opción activa) y placeholders deshabilitados para futuras opciones (spec 05, reemplaza a `home_view.py`/`HomeView` de la spec 04).
- `view/ocr_view.py` — `OcrView`, widgets PySide6 del flujo de OCR (abrir imagen, idioma, transcribir, preview, resultado), sin botón "Volver" desde la spec 05 (ya no hace falta con el sidebar siempre visible).
- `controller/ocr_controller.py` — `OcrController` y `AppState`, conecta los widgets de `OcrView` con el Model, incluye manejo de errores (imagen inválida, Tesseract no encontrado, fallo de transcripción) vía `QMessageBox`/`QFileDialog`, y threading con `QThread` + señales para el contador de segundos en transcripciones largas.
- `requirements.txt` — `pytesseract`, `Pillow`, `numpy`, `opencv-python`, `PySide6`.
- `config.json` — generado en runtime (no versionado, está en `.gitignore`), incluye `tesseract_path` (cuando el usuario configura una ruta manual) y `theme` (default `"dark"`).

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
