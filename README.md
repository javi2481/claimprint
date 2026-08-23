# Claimprint

[![CI](https://github.com/javi2481/claimprint/actions/workflows/ci.yml/badge.svg)](https://github.com/javi2481/claimprint/actions/workflows/ci.yml)

**English** · [Español](README.es.md)

**Claims-first IDP — first instance: finance (BYMA).**  
**Rule: no claim, no answer.**

## The problem

In a BYMA quarterly filing, "resultado neto 1T26" has two neighboring P&L rows. A RAG stack can retrieve the correct page and still answer with the wrong one.

| | Value |
|--|--|
| Question | ¿Cuál es el resultado neto del período 1T26? |
| Wrong neighbor (controlante) | 21259769 |
| Claimprint (consolidado) | **21262335** |

This isn't a rounding error. It's row identity — attributing the *controlante* figure when the question asked for *consolidado*. For an analyst, an auditor, or a compliance team automating extraction over filings, that mismatch means every model built on top of the answer is wrong in a way that looks right.

Claimprint resolves identity — issuer, period, scope, metric — before any answer is generated.

This architecture was born from a specific failure: a RAG stack retrieving the correct BYMA page but confidently outputting the *controlante* row instead of the *consolidado* row. Claimprint formalizes the fix: resolve identity as a typed claim before generation.

[`scripts/idp_ask.py`](scripts/idp_ask.py) answers the consolidated row from committed fixtures — no Docker, no API keys. See [Quick start](#quick-start).

## Who this is for

| Role | Context | What they get |
|------|---------|----------------|
| Research / equity analyst | Building models on financial statements, press releases, presentations | Figures with verified identity (consolidado vs controlante) |
| Auditor / controller | Reviewing automated extraction | Abstention when a question has no claim (no claim, no answer) |
| IDP / RAG engineer | Designing document → answer pipelines | Clear separation: claim = source of truth, chunk = derived input for chat |
| Compliance / risk | Automating over regulated filings | Provenance (page, row, filing) on every answer |

## How Claimprint works

Claimprint is a **claims-first IDP layer**, not a RAG wrapper. A document enters Document Intelligence (parse with MinerU, classify, extract) and becomes a **typed claim**: a structured figure with **identity** (which line item it is), **value**, and **provenance** (page, row, filing). Identity is resolved and verified before any answer is emitted. The primary path is **exact lookup** → verified answer. RAG chat is an **optional** layer that consumes verified claims; it is not the source of truth. If no claim passes verification, Claimprint **abstains** — no claim, no answer.

![Claimprint architecture — document to verified claim](docs/assets/claimprint-architecture.svg)

| Artifact | Role |
|----------|------|
| PDF | primary evidence |
| MinerU fixture | parsed representation |
| Recipe | extraction contract |
| Eval gold | test expectation |
| Claim | operational source of truth |
| RAG chunk | derived input for chat |
| Chat | consumer |

**Core concepts:** a **typed claim** is the verified figure (identity + value + provenance). A **recipe** is the extraction contract for a document class (e.g. [`recipes/financial_statement.json`](recipes/financial_statement.json)). A **projector** maps extracted rows onto that schema — resolving scope (consolidado vs controlante) along the way.

Details: [`docs/architecture.md`](docs/architecture.md)

## What the pilot proves

The **21.262.335 vs 21.259.769** trap is not anecdote — we ran it as an experiment.

If retrieval alone — keyword, vector, or hybrid — could resolve the identity trap, this architecture wouldn't be needed. We ran all three arms over the same corpus (n=20): they **tie** at Recall@5 **0.35** / MRR **0.2042**. That's not "the stack failed" — it's evidence that recovering the right PDF page is not enough when two neighboring rows share semantic context.

![Retrieval-only vs claims-first — identity trap](docs/assets/claimprint-retrieval-vs-chat.svg)

With claims injected (`push_claims`), claims-first chat scores **1.0** across `answer_value_match`, `citation_doc_match`, `evidence_doc_match`, and `abstention_correct` on n=10 task-specific cases. The jump isn't "better retrieval" — it's identity resolved before generation.

These are frozen live-pilot results from a manual run on a local RAGFlow stack (n=20 / n=10 — a small pilot, not a general IR benchmark). CI (`./scripts/check.sh` + pytest) validates contracts and scoring logic; it does not reproduce these scores. Gate 4 inject ablation in [`docs/evaluation.md`](docs/evaluation.md) shows how scores move by inject mode.

## What the clone includes

| Out of the box (no Docker) | Optional (you build locally) |
|----------------------------|------------------------------|
| BYMA PDFs + MinerU fixtures in [`fixtures/mineru/`](fixtures/mineru/) | RAGFlow stack via [`scripts/up.sh`](scripts/up.sh) |
| [`scripts/idp_ask.py`](scripts/idp_ask.py) — financial statements, press, presentation | Dataset **`demo_4`** indexed in the UI (not shipped in git) |
| Recipes, [`evals/`](evals/), pytest, [`scripts/check.sh`](scripts/check.sh) | Chat pilot + frozen metrics in [`docs/evaluation.md`](docs/evaluation.md) |
| HITL [`scripts/review_pack.py`](scripts/review_pack.py), dossier [`scripts/informe.py`](scripts/informe.py) | API keys in `.env` (Mistral + Voyage; gitignored) |

If you want the chat pilot, budget **x86_64**, **≥16 GB RAM**, and time to parse and index `demo_4` yourself.

## Quick start

```bash
git clone https://github.com/javi2481/claimprint.git
cd claimprint
uv venv && uv pip install -r requirements-dev.txt  # requires uv (https://astral.sh/uv) — or: python -m venv .venv && pip install -r requirements-dev.txt
./scripts/check.sh
python scripts/idp_ask.py "¿Cuál es el resultado neto del período 1T26?"
# → 21262335
python scripts/idp_ask.py "¿Cuál es la fecha del comunicado de prensa 1T26?"
# → 2026-05-08
python scripts/idp_ask.py "¿Cuál es el EBITDA de la presentación 1T26?"
# → 72128
python scripts/idp_ask.py "¿Cuál es el margen EBITDA LTM del comunicado de prensa 1T26?"
# → 76
python scripts/review_pack.py   # outputs/review/index.html (HITL)
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

**Abstain path**

```
Question: ¿Cuál fue el precio de cierre de YPF en BYMA el 3 de enero?
   ↓
Ambiguous / unsupported (off_corpus — no YPF price in corpus)
   ↓
ABSTAIN         route: abstain · claims: []
```

Extraction follows the same rule: if the issuer cannot be determined from text or filename, the document is skipped rather than defaulting to BYMA.

## Scope

| Included | Excluded |
|------|---------|
| First instance: BYMA PDFs in [`docs/archivos_muestra/`](docs/archivos_muestra/) | Docker volumes |
| Parsed text in [`fixtures/mineru/`](fixtures/mineru/) | Pre-built vector indexes or large external datasets |
| Recipes, `evals/`, pytest | API keys (Mistral, Voyage, …) |
| `scripts/idp_ask.py`, HITL, dossier | Pre-built RAG chunks or chat |

## Optional RAGFlow UI

Not required for identity lookup. Grounded-chat demo over the same corpus. Needs Docker Compose, **x86_64**, **≥16 GB RAM**, and local API keys (Mistral + Voyage). The clone does not include an indexed `demo_4`; live benchmark scores require rebuilding the stack locally.

```bash
cp .env.example .env   # add keys; .env is not in git
./scripts/check.sh
./scripts/up.sh        # UI: http://localhost
```

Enable Show Quote, empty response when no evidence, chat similarity threshold **0.2**, then `python scripts/push_claims.py` and a **new** chat. See [`docs/architecture.md`](docs/architecture.md) for inject lifecycle and [`docs/evaluation.md`](docs/evaluation.md) for pilot numbers.

```bash
docker compose --env-file .env \
  -f vendor/ragflow-docker/docker-compose.yml \
  -f docker-compose.overlay.yml down -v
```

## Documentation

| Doc | Contents |
|-----|----------|
| [`docs/architecture.md`](docs/architecture.md) | Identity, provenance, claim contract, inject lifecycle; "kernel" as a technical term |
| [`docs/evaluation.md`](docs/evaluation.md) | Gate 3 numbers, Gate 4 ablation, scoring |
| [`docs/archivos_muestra/README.md`](docs/archivos_muestra/README.md) | BYMA sample PDFs |

## What this demonstrates, what's next

Claimprint shows that document AI over financial filings fails at **identity**, not at retrieval depth or embedding quality — the same **21.262.335 vs 21.259.769** trap that started this project. The BYMA instance is frozen and reproducible: recipes, evals, abstention, optional RAGFlow UI. It is not a general IR benchmark, and it is not yet a second vertical.

Next: harden provenance (bbox-level source), tighten chat inject rules (deck vs financial statements), and validate the recipe/projector pattern on another document class before generalizing beyond finance.

## License

Claimprint (this repository's own code) is **Apache-2.0**; see [`LICENSE`](LICENSE). Vendored RAGFlow `docker/` is redistributed unmodified under Apache-2.0. Cite as [`CITATION.cff`](CITATION.cff).
