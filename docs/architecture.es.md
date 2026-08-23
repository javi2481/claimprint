[English](architecture.md) · **Español** · [README](../README.md) · [README ES](../README.es.md)

# Arquitectura

Para el problema, origen y resultados del piloto, ver el [README](../README.md) (English) o el [README ES](../README.es.md) (Español). Este documento es el **contrato técnico**: forma del claim, ciclo de inject, provenance y hooks de evaluación. "Kernel" abajo es terminología interna de la capa de claims — no es el hook de producto.

Claimprint es un **claims intelligence kernel**, no un wrapper de RAG. Un documento entra a Document Intelligence (parse, classify, extract) y se convierte en un **claim tipado**: cifra estructurada con **identidad**, **valor** y **provenance**. La identidad se resuelve y verifica antes de emitir cualquier respuesta.

## Capas fuente de verdad

| Artefacto | Rol |
|----------|-----|
| PDF | Evidencia primaria |
| Fixture MinerU | Representación parseada |
| Recipe | Contrato de extracción |
| Eval gold | Expectativa de test |
| Claim | Verdad operativa del kernel |
| Chunk RAG | Inject derivado para chat |
| Chat | Consumidor (no fuente de verdad) |

```text
PDF → MinerU fixture → recipe → eval gold → Claim → RAG chunk → chat
```

## Forma del claim

Identidad = `issuer · period · scope · metric`  
Provenance = `source_page · source_text · document_id · parse_artifact_hash · source_bbox`

Ejemplo (hashes truncados):

```json
{
  "identity_key": "BYMA|2026-03-31|consolidado|resultado_neto",
  "value": "21262335",
  "period": "2026-03-31",
  "source_page": 4,
  "source_text": "RESULTADO NETO DEL PERÍODO",
  "document_id": "a3f2…",
  "parse_artifact_hash": "9c1b…",
  "source_bbox": [0.12, 0.48, 0.71, 0.53]
}
```

**Claim = value + identity + provenance.**

El constructor aplica el contrato del claim: valor y período no vacíos, `source_page` null o > 0, `identity_key` consistente, y límites normalizados de `source_bbox` cuando está definido.

## Identidad vs provenance

- **Identidad** desambigua filas vecinas del P&L (consolidado vs controlante).
- **Provenance** ubica la evidencia en el PDF. `document_id` es SHA-256 de los bytes del PDF; `parse_artifact_hash` es SHA-256 del artefacto parse `.md` (no del PDF).

### Bbox de evidencia best-effort

`source_bbox` es un **bbox de evidencia best-effort**, no anotación de layout ground-truth.

`match_bbox()` puntúa texto ContentSpan contra `source_text` y/o el valor del claim y elige el mejor span. Eso ubica texto con evidencia; no garantiza que el bbox coincida con el límite exacto de la fila financiera.

La geometría de provenance puede originarse en:

- Coordenadas **MinerU content-list** (normalizadas 0–1 vía tamaño de página), o
- Posiciones de chunks **RAGFlow** cuando el sidecar cae a geometría de chunk.

`spans_from_ragflow_chunks()` normaliza contra el máximo de coordenadas observadas en esa página, no dimensiones físicas de página. Sin match en sidecar → `source_bbox=null` (nunca inventado).

HITL: `python scripts/review_pack.py` → `outputs/review/index.html` con overlay bbox (requiere `pdftoppm` para thumbnail; fallback wireframe si no).

## Resolución de período (press / presentation)

El período trimestral sigue precedencia **front_matter → body → filename**. Gana el primer match unívoco; front matter manda sobre body y filename.

No es detección de conflicto: si front matter dice 1T26 y body 2T26, gana front matter. No hay abstención por conflicto en v1.

## Selección de página

`select_page()` es **routing determinístico por keywords**, no ranking layout-aware: se elige la primera página cuyo texto folded contiene alguna keyword de la recipe. Funciona en el corpus BYMA controlado; sin corroboración estructural.

## Heurística de columnas P&L

Para extracción EEFF, el parser trata el **primer monto en una línea matched como período actual** y el **segundo como comparativo anterior**. Son heurísticas posicionales de layout para el orden de columnas BYMA, no comprensión semántica de columnas.

## Stack IDP

| Capa | Rol | Verificación |
|------|-----|--------------|
| **IDP** | fixtures → classify → extract → claims → `idp_ask` | `./scripts/check.sh` |
| **RAG** | RAGFlow + Infinity + Voyage + Mistral (`demo_4`) | Opcional, stack Docker ≥16 GB |

Contratos: `recipes/financial_statement.json`, `press_release.json`, `results_presentation.json`, más evals en [`evals/`](../evals/).

## Ciclo de inject RAGFlow

`scripts/up.sh` levanta el stack opcional. `python scripts/push_claims.py` es un paso **separado** post-setup.

- Scope: solo dataset `demo_4`, chat `chat_demo_4`.
- Mutaciones: DELETE chunks inject IDP previos, POST reemplazo, PUT prompt.
- Orden de replace: **POST chunk nuevo primero**, luego DELETE IDs de inject previos desde snapshot pre-POST. Un POST fallido deja chunks existentes.
- No transaccional: el PUT del prompt puede fallar después del replace de chunks. Solo scope demo-local.

### RAGFlow HTTP (conveniencia demo local)

`schemas/ragflow_http.py` puede leer `RAGFLOW_API_KEY` desde `.env` o hacer fallback a `SELECT token FROM api_token` vía contenedor MySQL de Compose (`claimprint-mysql-1`). Es **conveniencia demo local**, no contrato de integración pública.

## Layout

| Path | Rol |
|------|-----|
| `schemas/` / `recipes/` / `evals/` | Identidad tipada |
| `fixtures/mineru/` | Parse durable (texto identidad) |
| `scripts/idp_ask.py` | Lookup; cache en `outputs/claims.json` |
| `scripts/check.sh` | Contratos + pytest |
| `scripts/review_pack.py` / `informe.py` | HITL y dossier académico |
| `docs/archivos_muestra/` | PDFs BYMA |
| `scripts/up.sh` / `push_claims.py` | Stack RAG opcional |
| `vendor/ragflow-docker/` | Pin RAGFlow v0.26.4 (no editar) |
