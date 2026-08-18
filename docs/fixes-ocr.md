# Fixes menores de OCR (Tesseract)

Registro de correcciones acotadas al motor Tesseract que no ameritaron una spec
formal, generadas por la skill `/tesseract-bug`. Los cambios con trade-off para
el usuario viven en `specs/`, no acá.

Formato de cada entrada, la más reciente arriba:

```markdown
## AAAA-MM-DD — Título corto del síntoma

**Síntoma:** qué transcribió mal y en qué flujo.
**Causa:** archivo y línea, con la explicación técnica.
**Cambio:** qué se modificó.
**Verificación:** cómo se comprobó manualmente.
**Rama:** fix-ocr-<slug>
```
