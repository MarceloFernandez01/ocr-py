# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Alcance del proyecto

MVP de un aplicativo de escritorio en Python para OCR (Optical Character Recognition): transcribe imágenes a texto en español e inglés, reconociendo la mayor cantidad de fuentes posible.

Restricciones del proyecto (definidas en `readme.md`) y decisiones técnicas cerradas en `specs/01-mvp-ocr-tesseract-tkinter.md`:

- **Evitar módulos externos salvo que sea estrictamente necesario.** Las dependencias externas aprobadas son `pytesseract` (motor OCR), `Pillow` (decodificación de imágenes en cualquier formato para la vista previa en GUI), `numpy` y `opencv-python` (preprocesamiento de imagen para OCR sobre fondos complejos, ver `specs/03-preprocesamiento-ocr.md`). No agregar otras sin pasar antes por una spec.
- **Respetar el patrón MVC** (Modelo-Vista-Controlador) en la organización del código: `model/` (lógica de OCR y config, sin importar Tkinter), `view/` (ventana y widgets Tkinter, sin llamar a `pytesseract` directamente), `controller/` (conecta eventos de la vista con el modelo).
- **GUI sí está en alcance** (Tkinter, de la librería estándar), pero **sin diseño pulido ni estilo "metro"** por ahora — interfaz puramente funcional.
- **Motor OCR: Tesseract vía `pytesseract`.** El usuario debe instalar Tesseract-OCR manualmente en el sistema (no se instala vía pip ni se instala automáticamente desde la app). La app detecta la ruta por PATH; si no la encuentra, pide la ruta manualmente y la persiste en `config.json`.
- **Selector de idioma con 3 opciones fijas:** Español (`spa`), Inglés (`eng`), Ambos (`spa+eng`). Idiomas adicionales quedan para specs futuras.
- **Fuera de alcance del MVP:** OCR en vivo/captura de pantalla, guardado del texto a archivo o historial entre sesiones, instalación automática de Tesseract, motor ICR o pre-procesamiento de imagen.
- **El código debe estar documentado.** Cada módulo, clase y función pública lleva un docstring explicando su propósito (qué hace, parámetros y valor de retorno cuando no sean obvios). Esto tiene prioridad sobre la preferencia global de evitar comentarios/documentación innecesaria.

El MVP descrito en `specs/01-mvp-ocr-tesseract-tkinter.md` ya está implementado. Estructura actual del código:

- `main.py` — punto de entrada; instancia `MainView` y `OcrController` y arranca el loop de Tkinter.
- `model/config_model.py` — `load_config()` / `save_tesseract_path()`, lee/escribe `config.json`.
- `model/tesseract_locator.py` — `resolve_tesseract_path()`, detecta Tesseract por PATH o por `config.json`.
- `model/ocr_model.py` — `transcribe(image_path, language_code, tesseract_path)`, envuelve `pytesseract`.
- `view/main_view.py` — `MainView`, todos los widgets Tkinter y sus setters/getters.
- `controller/ocr_controller.py` — `OcrController` y `AppState`, conecta los botones de la vista con el Model, incluye manejo de errores (imagen inválida, Tesseract no encontrado, fallo de transcripción).
- `requirements.txt` — `pytesseract`, `Pillow`, `numpy`, `opencv-python`.
- `config.json` — generado en runtime (no versionado, está en `.gitignore`), solo cuando el usuario configura una ruta manual de Tesseract.

No hay comandos de build/lint/test configurados en el repo (no hay `pyproject.toml` ni `Makefile`). Para correr la app: `python main.py`. Antes de asumir que existe un comando de test o lint, verificar con `ls`.

Limitación conocida (no resuelta, candidata a spec futura): la transcripción no maneja bien imágenes muy grandes.

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
