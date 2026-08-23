**English** · [Español](architecture.es.md) · [README](../README.md) · [README ES](../README.es.md)

# Architecture

For the problem, origin story, and pilot results, see the [README](../README.md) (English) or [README ES](../README.es.md) (Español). This document is the **technical contract**: claim shape, inject lifecycle, provenance, and evaluation hooks. "Kernel" below is internal terminology for the claims layer — not the product hook.

Claimprint is a **claims intelligence kernel**, not a RAG wrapper. A document enters Document Intelligence (parse, classify, extract) and becomes a **typed claim**: structured figure with **identity**, **value**, and **provenance**. Identity is resolved and verified before any answer is emitted.

## Source-of-truth layers

| Artifact | Role |
|----------|------|
| PDF | Primary evidence |
| MinerU fixture | Parsed representation |
| Recipe | Extraction contract |
| Eval gold | Test expectation |
| Claim | Operational kernel truth |
| RAG chunk | Derived inject for chat |
| Chat | Consumer (not source of truth) |

```text
PDF → MinerU fixture → recipe → eval gold → Claim → RAG chunk → chat
```

## Claim shape

Identity = `issuer · period · scope · metric`  
Provenance = `source_page · source_text · document_id · parse_artifact_hash · source_bbox`

Example (hashes truncated):

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

The constructor enforces the claim contract: non-empty value and period, `source_page` null or > 0, consistent `identity_key`, and normalized `source_bbox` bounds when set.

## Identity vs provenance

- **Identity** disambiguates neighboring P&L rows (consolidado vs controlante).
- **Provenance** locates evidence in the PDF. `document_id` is SHA-256 of the PDF bytes; `parse_artifact_hash` is SHA-256 of the parse `.md` artifact (not the PDF).

### Best-effort evidence bbox

`source_bbox` is a **best-effort evidence bbox**, not ground-truth layout annotation.

`match_bbox()` scores ContentSpan text against `source_text` and/or the claim value and picks the best span. That locates evidence-bearing text; it does not guarantee the bbox matches the exact financial row boundary.

Provenance geometry may originate from:

- **MinerU content-list** coordinates (normalized 0–1 via page size), or
- **RAGFlow chunk positions** when the sidecar falls back to chunk geometry.

`spans_from_ragflow_chunks()` normalizes against the maximum observed coordinates on that page, not physical page dimensions. No sidecar match → `source_bbox=null` (never invented).

HITL: `python scripts/review_pack.py` → `outputs/review/index.html` with bbox overlay (requires `pdftoppm` for thumbnail; wireframe fallback otherwise).

## Period resolution (press / presentation)

Quarter period follows **front_matter → body → filename** precedence. The first unambiguous match wins; front matter takes authority over body and filename.

This is not conflict detection: if front matter says 1T26 and body says 2T26, front matter wins. There is no abstain-on-conflict in v1.

## Page selection

`select_page()` is **deterministic keyword routing**, not layout-aware ranking: the first page whose folded text contains any recipe keyword is selected. Works on the controlled BYMA corpus; no structural corroboration.

## P&L column heuristic

For EEFF extraction, the parser treats the **first amount on a matched line as current period** and the **second as comparative prior**. This is positional layout heuristics for the BYMA column order, not semantic column understanding.

## IDP stack

| Layer | Role | Verification |
|------|--------|----------------|
| **IDP** | fixtures → classify → extract → claims → `idp_ask` | `./scripts/check.sh` |
| **RAG** | RAGFlow + Infinity + Voyage + Mistral (`demo_4`) | Optional, ≥16 GB Docker stack |

Contracts: `recipes/financial_statement.json`, `press_release.json`, `results_presentation.json`, plus evals under [`evals/`](../evals/).

## RAGFlow inject lifecycle

`scripts/up.sh` starts the optional stack. `python scripts/push_claims.py` is a **separate** post-setup step.

- Scope: dataset `demo_4`, chat `chat_demo_4` only.
- Mutations: DELETE prior IDP inject chunks, POST replacement, PUT prompt.
- Replace order: **POST new chunk first**, then DELETE prior inject chunk IDs from a pre-POST snapshot. A failed POST leaves existing chunks in place.
- Not transactional: prompt PUT can still fail after chunk replace. Demo-local scope only.

### RAGFlow HTTP (local demo convenience)

`schemas/ragflow_http.py` may read `RAGFLOW_API_KEY` from `.env` or fall back to `SELECT token FROM api_token` via the Compose MySQL container (`claimprint-mysql-1`). This is **local demo convenience**, not a public integration contract.

## Layout

| Path | Role |
|------|-----|
| `schemas/` / `recipes/` / `evals/` | Typed identity |
| `fixtures/mineru/` | Durable parse (identity text) |
| `scripts/idp_ask.py` | Lookup; cache in `outputs/claims.json` |
| `scripts/check.sh` | Contracts + pytest |
| `scripts/review_pack.py` / `informe.py` | HITL and academic dossier |
| `docs/archivos_muestra/` | BYMA PDFs |
| `scripts/up.sh` / `push_claims.py` | Optional RAG stack |
| `vendor/ragflow-docker/` | RAGFlow v0.26.4 pin (do not edit) |
