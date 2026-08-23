# Claimprint

[![CI](https://github.com/javi2481/claimprint/actions/workflows/ci.yml/badge.svg)](https://github.com/javi2481/claimprint/actions/workflows/ci.yml)

**Kernel:** claims intelligence  
**First instance:** finance / BYMA  
**Rule:** no claim, no answer.

Claimprint extracts and evaluates structured claims before retrieval-augmented generation is allowed to answer. This repository ships the **first instance**: finance, over BYMA statements in [`docs/archivos_muestra/`](docs/archivos_muestra/). Other verticals would add recipes and projectors; they are not in this tree.

Recipes and [`evals/`](evals/) define the figures. The RAGFlow chat consumes them and is **not** the source of truth.

## The problem

Unspecified “net income 1T26” has two neighboring P&L rows. Retrieval can return the controlling interest. The kernel does not.

| | Value |
|--|--|
| Question | ¿Cuál es el resultado neto del período 1T26? |
| Wrong neighbor (controlante) | 21259769 |
| Claimprint (consolidado) | **21262335** |

Identity lookup: no Docker, no API keys.

### How Claimprint works

Claimprint is a **claims intelligence kernel**, not a RAG wrapper. A document enters Document Intelligence (parse, classify, extract) and becomes a **typed claim**: a structured figure with **identity** (which line item it is), **value**, and **provenance** (page, row, filing). Identity is resolved and verified before any answer is emitted. The primary path is **exact lookup** → verified answer. RAG chat is an **optional** layer that consumes verified claims; it is not the source of truth. If no claim passes verification, the kernel **abstains**—no claim, no answer.

![Claimprint architecture — document to verified claim](docs/assets/claimprint-architecture.svg)

### Why retrieval alone is not enough

The pilot compares retrieval-only search (PDF+page, **no claim inject**) against **claims-first** grounded chat (**after** `push_claims` injects IDP figures).

Retrieval (n=20): keyword, vector, and hybrid **tie** at Recall@5 **0.35** and MRR **0.2042**. The pilot does **not** show hybrid winning. The underlying issue is the **identity trap**: retrieval can return evidence for a correct number attached to the wrong figure—consolidado vs controlante in the table above.

Claims-first chat (n=10, post-`push_claims`): answer_value_match / citation_doc_match / evidence_doc_match / abstention_correct **1.0**. **answer_value_match** is exact-value **containment** (expected digits appear in the reply; not full semantic accuracy). **abstention_correct** is correct behavior (abstain when gold says so; do not abstain when an answer is required). evidence_doc_match/citation_doc_match averages skip abstain-only cases. Task-specific scores on a small corpus (`demo_4` 10/10); knobs: Mistral `mistral-small-latest`, Voyage, similarity threshold **0.2**, rerank on, IDP inject. Not a general IR paper. Gate-3 remeasure (post page-hit fix + renamed chat keys): retrieval MRR **0.2042**; chat still **1.0**/n=10. Hits without a resolvable page are dropped (no invented page 1).

![Retrieval-only vs claims-first — identity trap](docs/assets/claimprint-retrieval-vs-chat.svg)

Parsed BYMA text lives in [`fixtures/mineru/`](fixtures/mineru/). [`scripts/idp_ask.py`](scripts/idp_ask.py) answers that question from those fixtures. The RAGFlow UI is optional (≥16 GB RAM and local API keys). `.env` is gitignored.

## Quick start

```bash
git clone https://github.com/javi2481/claimprint.git
cd claimprint
uv venv && uv pip install -r requirements-dev.txt
./scripts/check.sh
python scripts/idp_ask.py "¿Cuál es el resultado neto del período 1T26?"
# → 21262335
python scripts/idp_ask.py "¿Cuál es la fecha del comunicado de prensa 1T26?"
# → 2026-05-08
python scripts/idp_ask.py "¿Cuál es el EBITDA de la presentación 1T26?"
# → 72128
python scripts/idp_ask.py "¿Cuál es el margen EBITDA LTM del comunicado de prensa 1T26?"
# → 76
python scripts/review_pack.py   # outputs/review.html (HITL)
python scripts/informe.py       # outputs/dossier.html
```

On Windows, run `./scripts/check.sh` from Git Bash or WSL.

## Terminal flow

Two paths through `idp_ask`: answer when a verified claim exists, abstain when the question is off-corpus or unsupported.

**Answer path**

```
Question: ¿Cuál es el resultado neto del período 1T26?
   ↓
Identity intent (consolidado | resultado_neto | 2026-03-31)
   ↓
Candidate claims (from fixtures → extract → store)
   ↓
Verified claim  BYMA|2026-03-31|consolidado|resultado_neto = 21262335
   ↓
Answer          21262335  (page 4, RESULTADO NETO DEL PERÍODO)
```

```bash
python scripts/idp_ask.py "¿Cuál es el resultado neto del período 1T26?"
# route: identity · claims[0].value: 21262335
```

**Abstain path**

```
Question: ¿Cuál fue el precio de cierre de YPF en BYMA el 3 de enero?
   ↓
Ambiguous / unsupported (off_corpus — no YPF price in corpus)
   ↓
ABSTAIN         route: abstain · claims: []
```

```bash
python scripts/idp_ask.py "¿Cuál fue el precio de cierre de YPF en BYMA el 3 de enero?"
# route: abstain · abstain_reason: off_corpus
```

Extraction follows the same rule: if the issuer cannot be determined from text or filename, the document is skipped rather than defaulting to BYMA.

## Scope

| Included | Excluded |
|------|---------|
| First instance: BYMA PDFs in `docs/archivos_muestra/` | Docker volumes |
| Parsed text in `fixtures/mineru/` | Indexed `demo_4` dataset |
| Recipes, `evals/`, pytest | API keys (Mistral, Voyage, …) |
| `scripts/idp_ask.py`, HITL, dossier | Pre-built RAG chunks or chat |

## Architecture

| Layer | Role | Verification |
|------|--------|----------------|
| **IDP** | fixtures → classify → extract → claims → `idp_ask` | `./scripts/check.sh` |
| **RAG** | RAGFlow + Infinity + Voyage + Mistral (`demo_4`) | Optional, ≥16 GB Docker stack |

Contracts: `recipes/financial_statement.json`, `press_release.json`, `results_presentation.json`, plus [`evals/identity_v1.json`](evals/identity_v1.json), [`identity_v2.json`](evals/identity_v2.json), [`press_v1.json`](evals/press_v1.json), and [`presentation_v1.json`](evals/presentation_v1.json).

Identity traps: an unspecified controlling interest defaults to consolidated. Net income or tax **from the press release** or **from the presentation** abstains. EBITDA in millions comes from the **presentation**; LTM margin `76`/`75` appears in **press release and presentation**. YPF / annual report abstains.

Evaluation catalog: four layers (files → identity → inject mock → live RAG). Contracts live in [`evals/`](evals/); pilot numbers are in **The problem** above and **Optional RAGFlow UI** below.

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
| `docs/assets/claimprint-architecture.svg` | README architecture diagram |
| `docs/assets/claimprint-retrieval-vs-chat.svg` | README retrieval vs claims-first |
| `docs/assets/claimprint-linkedin.svg` | LinkedIn post card (export to PNG) |

---


## Two pilots (not one "RAG accuracy")

**Experiment 1 — Retrieval (no claims).** Can the stack recover the right PDF+page?
Metrics: Recall@5 / Recall@10 / MRR. Small pilot, not a general IR benchmark.

**Experiment 2 — Claim-grounded generation (after `push_claims`).** Can chat answer
when verified claims are injected? Metrics: `answer_value_match`, `citation_doc_match`,
`evidence_doc_match`, `abstention_correct` on n=10 task-specific cases (`demo_4`).
Never reported as "RAG accuracy 100%".

**Evidence chain (gold ≠ source of truth):**

```text
PDF → MinerU fixture → recipe → eval gold → Claim → RAG chunk → chat
```

| Artifact | Role |
|----------|------|
| PDF | primary evidence |
| MinerU fixture | parsed representation |
| Recipe | extraction contract |
| Eval gold | test expectation |
| Claim | operational kernel truth |
| RAG chunk | derived inject for chat |
| Chat | consumer |

Identity vs provenance (v1.0): identity = issuer · period · scope · metric;
provenance = source_page · source_text · optional `document_id` (sha256 del PDF) ·
optional `source_bbox` (normalizado 0–1 desde sidecar MinerU). Press/presentation **period** is content-first
(portada / `front_matter`, then filename). Sin match en el sidecar → `source_bbox=null` (no inventar).

`scripts/up.sh` starts the optional stack. `python scripts/push_claims.py` is a **separate**
post-setup step and mutates only dataset `demo_4` and chat `chat_demo_4`.
Chat gains also depend on the controlled IDP instruction block (claims + prompt rules).

## Optional RAGFlow UI

This stack is not required for identity lookup. It is a grounded-chat demo over the same corpus. It needs Docker Compose, **x86_64**, **≥16 GB RAM**, and local API keys (Mistral + Voyage). The clone does not include an indexed `demo_4`.

```bash
cp .env.example .env   # add keys; .env is not in git
./scripts/check.sh
./scripts/up.sh        # UI: http://localhost
```

Stack: RAGFlow v0.26.4 + Infinity + MinerU `pipeline` + Mistral `mistral-small-latest` + Voyage. On Linux set `vm.max_map_count` ≥ 262144; add Mistral and Voyage under RAGFlow Model providers (chat is not auto-read from `.env`). Enable Show Quote, empty response when no evidence, chat similarity threshold **0.2**, then `python scripts/push_claims.py` and a **new** chat.

Infinity scores full-text with **BM25**. The `keyword` / `vector` / `hybrid` arms are RAGFlow knobs (`vector_similarity_weight` 0 / 1 / 0.3), not a custom Okapi library.

Pilot evaluation (n=20 retrieval; n=10 chat; corpus `demo_4` 10/10):

| Arm | Recall@5 | Recall@10 | MRR |
|-------|----------|-----------|-----|
| keyword | 0.35 | 0.35 | 0.2042 |
| vector | 0.35 | 0.35 | 0.2042 |
| hybrid | 0.35 | 0.35 | 0.2042 |

The three arms tie: this pilot does **not** show hybrid winning. That tie is evidence for claims-first: page-level retrieval alone does not clear the consolidado / controlante trap.

| Layer | What it measures | Score |
|-------|------------------|-------|
| Retrieval only | PDF+page, no claim inject | Recall@5 **0.35** (n=20) |
| Chat after `push_claims` | IDP inject; answer = value containment; abstention = correct abstain / no false abstain | answer_value_match / citation_doc_match / evidence_doc_match / abstention_correct **1.0** (n=10) |

The gap between retrieval-only and claims-first chat is the argument, not a number to hide. Small-n pilot — honest, not a paper IR claim. Dumps live in `outputs/` (gitignored).

### Gate 4 — inject ablation (chunk vs prompt)

Separates **EEFF chunk inject** from **IDP prompt rules** on the same n=10 gold (`evals/rag_chat_v1.json`). Does not replace the frozen Gate-3 row above.

| Arm | `--inject-mode` | IDP chunk | IDP prompt rules |
|-----|-----------------|-----------|------------------|
| A | `off` | off | off |
| B | `chunks` | on | off |
| C | `full` | on | on (pilot default) |

```bash
python scripts/push_claims.py --inject-mode full   # restore pilot default
python scripts/rag_ablation.py                   # → outputs/rag_ablation.json
python scripts/clear_chat_sessions.py              # optional: drop UI sessions after long runs
```

`rag_ablation.py` re-applies each arm via `push_claims`, runs the ten gold questions (35 s spacing), restores `full`, and writes a separate dump. Run only on a live `demo_4` + `chat_demo_4` stack.

```bash
docker compose --env-file .env \
  -f vendor/ragflow-docker/docker-compose.yml \
  -f docker-compose.overlay.yml down -v
```

---

## License

Claimprint (this repository's own code) is **Apache-2.0**; see [`LICENSE`](LICENSE). Vendored RAGFlow `docker/` is redistributed unmodified under Apache-2.0. Cite as [`CITATION.cff`](CITATION.cff).
