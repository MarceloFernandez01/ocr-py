---
name: tesseract-bug
description: Reporta un fallo de reconocimiento del motor Tesseract a partir de una descripción y una imagen, lo diagnostica contra el pipeline de OCR y decide si amerita una spec formal o un fix acotado documentado en docs/fixes-ocr.md.
disable-model-invocation: true
argument-hint: 'descripción corta del síntoma (adjuntar imagen si es posible)'
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(git status:*), Bash(git branch:*), Bash(git checkout:*), Bash(ls:*)
---

# /tesseract-bug — Reporte y corrección de fallos de reconocimiento

Esta skill recibe el reporte de un usuario sobre un fallo de reconocimiento del
motor Tesseract, lo diagnostica contra el pipeline real de OCR del proyecto, y
según el trade-off del arreglo lo resuelve por uno de dos caminos: un fix
acotado en una rama propia, o una spec formal redactada por esta misma skill.

**Cubre únicamente el motor Tesseract.** Bugs del motor Claude Haiku quedan
fuera de esta skill.

## Session context

Estado actual del repositorio:
!`git status --short`

Rama actual:
!`git branch --show-current`

Changelog de fixes existente:
!`ls docs/fixes-ocr.md 2>/dev/null || echo "docs/fixes-ocr.md no existe todavía"`

---

## Instrucciones

Seguir las cinco fases en orden estricto. **No avanzar a la siguiente fase si
la anterior no se completó correctamente.**

---

### Fase 1 — Recibir el reporte

El argumento recibido es: `$ARGUMENTS`

Si `$ARGUMENTS` viene vacío, pedir al usuario una descripción del síntoma en
una sola oración.

Pedir la imagen del caso: una ruta de archivo o la imagen pegada directamente
en el chat. Si el usuario no tiene imagen disponible, continuar igual,
dejando registrado en el diagnóstico que se hace sin evidencia visual.

Preguntar en un único bloque (nunca de a una pregunta por vez), aceptando que
varias ya vengan respondidas en la descripción inicial:

1. ¿En qué flujo ocurre: OCR de imágenes o OCR en vivo?
2. ¿Qué idioma estaba seleccionado (Español, Inglés, Ambos)?
3. ¿Qué texto debería haber salido y qué salió realmente?
4. ¿Había recorte de región o zoom activo? (solo aplica a OCR de imágenes)
5. ¿Qué motor OCR estaba configurado: Tesseract o Claude Haiku?

**Regla de corte del motor.** Si la respuesta a la pregunta 5 es Claude
Haiku, detenerse de inmediato con este mensaje y no continuar a la Fase 2:

```
❌ Esta skill solo cubre el motor Tesseract.

El caso reportado ocurrió con el motor Claude Haiku configurado. Para
diagnosticarlo, reproduce el mismo caso con Tesseract seleccionado en
Configuración y vuelve a invocar /tesseract-bug.
```

---

### Fase 2 — Analizar

Leer la imagen adjunta con `Read` y describir qué se observa que pueda
explicar el fallo: tipografía, tamaño del texto en píxeles, contraste, fondo,
bordes o subrayados, dimensiones totales de la imagen.

Correlacionar la observación con los puntos reales del pipeline de OCR — no
buscarlos a ciegas, son estos:

- `model/ocr_model.py:55-94` — `transcribe_image_variants`, punto único
  donde se invoca Tesseract. Las tres funciones públicas del módulo
  (`transcribe_large_image`, `transcribe_cropped_image`,
  `transcribe_image_variants`) delegan aquí, así que un cambio de
  configuración corrige a la vez OCR en vivo, OCR estático, con tiling y
  con recorte de región.
- `model/ocr_model.py:72` — `tesseract_config`, hoy
  `"-c tessedit_char_blacklist=|"` (fix de la spec 14). Se pasa a
  `pytesseract.image_to_data` (`:78-80`, usada para puntuar cada variante) y
  a `pytesseract.image_to_string` (`:94`, llamada final). Es la palanca de
  cualquier ajuste de configuración de Tesseract; hoy no se pasan `--psm` ni
  `--oem`.
- `model/ocr_model.py:74-92` — selección de la mejor variante por confianza
  promedio. `best_variant` arranca en la variante `original` (índice 0) y
  solo se reemplaza con `>` estricto (`:90`), así que ante empate de
  confianza gana siempre `original`.
- `model/image_preprocessing.py:11-39` — `generate_variants`, las 6
  variantes fijas: `original`, `gris_autocontraste`, `otsu`,
  `otsu_invertido`, `adaptativo`, `canal_color`. Las cuatro binarizaciones
  parten del mismo gris autocontrastado de `:24`, así que un mal
  autocontraste degrada 4 de las 6 variantes a la vez.
- `model/image_preprocessing.py:42` — `_upscale_if_needed`, umbral
  `MIN_TEXT_HEIGHT = 150` sobre el **alto total de la imagen**, no sobre el
  alto del texto. Sospechoso cuando el texto es chico dentro de una imagen
  grande.
- `model/image_tiling.py:24` — sobre 3000 px de lado se parte en grilla de
  hasta 3x3 con 10% de solapamiento, y el texto solapado **no se
  deduplica**. Sospechoso cuando aparece texto repetido en los bordes.

Presentar una hipótesis de causa apuntando a un archivo y línea concretos,
mencionando las alternativas descartadas y por qué.

---

### Fase 3 — Clasificar por trade-off

Antes de proponer cualquier cambio, enunciar de forma explícita qué se
pierde con el arreglo propuesto:

- **Sin trade-off perceptible** (el arreglo no degrada ningún otro caso de
  uso) → camino fix directo, ir a Fase 4.
- **Con trade-off** (el arreglo sacrifica otro caso de uso — el ejemplo de
  referencia es la spec 14, que a cambio de arreglar la confusión "I" dejó
  de reconocer el pipe "|" literal para siempre) → camino spec, ir a Fase 5.

Ante duda sobre si un trade-off es perceptible, tratar el caso como spec: es
la opción reversible, porque no toca código todavía.

---

### Fase 4 — Fix directo

**Nunca editar código antes de la confirmación.** Mostrar:

```
Rama actual: <la mostrada en el contexto de sesión>
Propongo crear: fix-ocr-<slug>

Diagnóstico: <causa, archivo:línea>
Cambio propuesto: <descripción concreta>
Trade-off: ninguno perceptible

¿Creo la rama y aplico el fix? [y/N]
```

**La rama es obligatoria, sin excepciones.** Esta skill siempre trabaja en
la rama `fix-ocr-<slug>` que ella misma crea, sin importar cuál sea la rama
de partida:

- Si el usuario responde que no, entregar el diagnóstico y **detenerse sin
  editar nada**. A diferencia de `/spec-impl`, esta skill **no ofrece** la
  alternativa de trabajar en la rama actual: no existe camino de fix sin
  rama propia.
- `master` y `main` están vetadas como rama de trabajo de forma explícita.
  Tras crear o cambiar de rama, verificar con `git branch --show-current`
  que el resultado no sea `master` ni `main`; si lo es, detenerse y
  reportarlo como error en vez de editar.
- Estar parado en otra rama de feature tampoco autoriza a editar ahí: se
  crea igual `fix-ocr-<slug>` a partir de esa rama.
- Si `fix-ocr-<slug>` ya existe, avisarlo y hacer `git checkout` sobre ella
  en vez de fallar.
- Si `git status --short` mostró cambios sin commitear en el contexto de
  sesión, avisarlo antes de crear la rama: esos cambios viajan a la rama
  nueva y se mezclarían con el fix.

Con un sí explícito y ya verificada la rama:

1. `git checkout -b fix-ocr-<slug>` (o `git checkout fix-ocr-<slug>` si ya
   existía).
2. Aplicar la edición concreta con `Edit`.
3. Anteponer una entrada nueva en `docs/fixes-ocr.md`, arriba de las
   existentes, siguiendo el formato documentado en ese archivo (Síntoma,
   Causa, Cambio, Verificación, Rama).

**Nunca hacer commit, merge ni push.** La rama queda con los cambios en el
árbol de trabajo para que el usuario los revise.

Cerrar indicando los pasos de verificación manual: correr `python main.py`,
reproducir el caso original y confirmar el resultado correcto, y transcribir
además una imagen que ya se reconocía bien antes del fix para confirmar que
no hay regresión.

---

### Fase 5 — Redactar la spec

**No tocar código ni ramas en este camino.** Esta skill escribe la spec
ella misma, con el mismo método que `/spec`, aprovechando que el
diagnóstico de las Fases 1 a 3 ya respondió gran parte de lo que `/spec`
preguntaría desde cero.

Antes de redactar:

1. Leer `template.md` en el directorio de la skill `spec`
   (`~/.agents/skills/spec/template.md` o la ruta equivalente donde esté
   instalada) — es la forma que la spec debe respetar, no texto para copiar
   literal.
2. Leer las dos specs más recientes de `specs/` para tomar las convenciones
   vigentes del repo (numeración, idioma de las etiquetas, formato de
   encabezado).

Preguntas de clarificación previas, en un solo bloque de 3 a 5, saltando las
que el diagnóstico ya dejó respondidas:

1. ¿El trade-off identificado se acepta tal cual, o el arreglo debe evitarlo
   aunque quede más complejo?
2. ¿El comportamiento nuevo queda fijo en el código o configurable desde la
   vista de Configuración?
3. ¿El arreglo aplica solo al síntoma reportado o cubre casos análogos?
   (ejemplo: solo "I" vs "|", o todo el grupo I/l/1)
4. ¿Se acota a un flujo (OCR de imágenes, OCR en vivo) o vale para los dos?

Redactar **sección por sección**, mostrando cada una en markdown y
preguntando "¿Esta sección queda así o la ajustamos?", sin avanzar hasta la
confirmación. Orden y formato del repo, siguiendo
`specs/14-fix-ocr-confusion-i-pipe.md` como ejemplo canónico:

1. **Encabezado** — `# Spec NN: Título`, y debajo `**Estado:** Draft`,
   `**Dependencias:**`, `**Fecha:**` y `**Objetivo:**` de una sola oración,
   sin blockquote (formato de las specs 13 y 14, el vigente).
2. **`## Alcance`** — con los dos sub-bloques obligatorios
   `**Dentro del alcance:**` y `**Fuera del alcance:**`. En este último
   entra lo que salió durante la conversación y se decidió diferir.
3. **`## Modelo de datos`** — si el arreglo no introduce estructuras nuevas
   ni toca `config.json`, decirlo explícitamente en una oración en vez de
   omitir la sección.
4. **`## Plan de implementación`** — pasos numerados, cada uno dejando la
   app ejecutable, cada uno con su "Prueba manual:" descrita. Un fix de
   reconocimiento suele ser un solo paso, y está bien que lo sea.
5. **`## Criterios de aceptación`** — checklist booleana `- [ ]`,
   verificable, incluyendo siempre un criterio de no regresión sobre una
   imagen que ya se transcribía bien.
6. **`## Decisions`** — viñetas `**Sí:**` / `**No:**` con justificación
   breve, registrando las alternativas descartadas durante el diagnóstico
   de la Fase 2.
7. **`## Identified risks`** — tabla `| Riesgo | Mitigación |`, donde el
   trade-off que llevó el caso a spec debe aparecer como riesgo asumido.

Al terminar todas las secciones:

1. Determinar el siguiente número secuencial mirando `specs/`.
2. Generar un slug corto a partir del objetivo.
3. Proponer el nombre de archivo al usuario y esperar su confirmación antes
   de escribir.
4. Crear el archivo en `specs/NN-slug.md` con todas las secciones
   aprobadas. Estado `Draft` siempre — **no marcar `Aprobado`
   automáticamente**, eso lo hace el usuario tras releerla.
5. Confirmar al usuario: ruta del archivo creado, recordatorio de que queda
   en `Draft`, y que el paso siguiente es aprobarla a mano y correr
   `/spec-impl NN-slug` para implementarla. **Detenerse ahí** — no proponer
   implementarla ni escribir código.

---

## Reglas duras

- Solo motor Tesseract. Bugs del motor Claude quedan fuera de esta skill.
- Nunca editar código sin un sí explícito del usuario.
- Nunca editar código en `master` ni en `main`, bajo ninguna circunstancia.
  Esta skill solo edita estando parada en la rama `fix-ocr-<slug>` que ella
  creó; si no logró crearla o el usuario la rechazó, no edita.
- Nunca hacer commit, merge ni push. La rama queda con los cambios sin
  commitear para que el usuario los revise.
- Nunca marcar un fix como verificado sin que el usuario lo haya probado en
  la app.
- Nunca escribir código en el camino de spec, ni marcarla `Aprobado`: se
  guarda como `Draft` y la aprueba el usuario.
- Nunca generar la spec completa de una sola vez: sección por sección, con
  confirmación en cada una.
- No ampliar el arreglo más allá del síntoma reportado; otras confusiones de
  caracteres son otro reporte, otra invocación de esta skill.
- Responder siempre en el mismo idioma del prompt inicial.

## Resumen de comportamiento esperado

```
/tesseract-bug "el texto sale con | en vez de I"
  [imagen adjunta]

  Fase 1  →  bloque de 5 preguntas de clarificación
             motor confirmado: Tesseract → continúa
  Fase 2  →  lee la imagen, apunta a model/ocr_model.py:72
  Fase 3  →  trade-off: bloquear "|" impide reconocerlo si aparece real
             → con trade-off → Fase 5

  Fase 5  →  preguntas previas de spec
             redacta specs/15-<slug>.md sección por sección
             guarda con **Estado:** Draft
             recuerda aprobarla a mano y correr /spec-impl 15-<slug>

/tesseract-bug "el guion largo sale como dos guiones cortos"
  [imagen adjunta]

  Fase 1  →  bloque de preguntas, motor: Tesseract → continúa
  Fase 2  →  apunta a model/image_preprocessing.py:24
  Fase 3  →  trade-off: ninguno perceptible → Fase 4

  Fase 4  →  muestra diagnóstico y pide confirmación [y/N]
             si "y": git checkout -b fix-ocr-<slug>, aplica el fix,
             antepone entrada en docs/fixes-ocr.md
             si "n": se detiene, no edita nada, no crea rama
```
