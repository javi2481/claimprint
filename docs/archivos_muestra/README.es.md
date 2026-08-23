[English](README.md) · **Español** · [README](../../README.md) · [README ES](../../README.es.md)

# Archivos de muestra (BYMA)

PDFs reales de BYMA. **Un parse MinerU**, dos capas: el IDP lee `fixtures/mineru/<stem>.md`; RAGFlow usa el dataset UI **`demo_4`**.

El clone de git trae los artefactos. Un clone **no** trae volúmenes Docker.

Orden demo: **configurar el dataset** (MinerU, español, KG/RAPTOR off) → **subir** → en cada file **Tamaño de la tarea por página = 128** → **Parse** de a uno → `python scripts/export_mineru.py` para pisar fixtures.

No actives Knowledge graph ni RAPTOR: no son parsers y gastan tokens del chat.

Detalle del stack opcional: sección **UI opcional RAGFlow** del [README ES](../../README.es.md) raíz (chat demo: Mistral + Voyage, threshold 0.2, luego `push_claims`).

## Orden de parseo

1. Comunicados y transcripción (pocas páginas).
2. Presentaciones.
3. EEFF (tablas; tarda en CPU).
4. Memorias (~190 páginas; al final).

No reusar `demo_3` ni files ya parseados con DeepDoc/Naive: **dataset nuevo**, subir de nuevo después de poner MinerU en Configuración. Cambiar el dropdown del dataset no reescribe el parser de cada file ni los chunks.
