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

| Artifact | Role |
|----------|------|
| PDF | primary evidence |
| MinerU fixture | parsed representation |
| Recipe | extraction contract |
| Eval gold | test expectation |
| Claim | operational kernel truth |
| RAG chunk | derived inject for chat |
| Chat | consumer |

Details: [`docs/architecture.md`](docs/architecture.md)

### Why retrieval alone is not enough

Retrieval-only search (PDF+page, **no claim inject**) ties at Recall@5 **0.35** and MRR **0.2042** (n=20). Claims-first chat after `push_claims` scores **1.0** on n=10 task-specific cases. The underlying issue is the **identity trap**: retrieval can return evidence for a correct number attached to the wrong figure.

![Retrieval-only vs claims-first — identity trap](docs/assets/claimprint-retrieval-vs-chat.svg)

Full methodology and numbers: [`docs/evaluation.md`](docs/evaluation.md)

Parsed BYMA text lives in [`fixtures/mineru/`](fixtures/mineru/). [`scripts/idp_ask.py`](scripts/idp_ask.py) answers from those fixtures. The RAGFlow UI is optional (≥16 GB RAM and local API keys). `.env` is gitignored.

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
| First instance: BYMA PDFs in `docs/archivos_muestra/` | Docker volumes |
| Parsed text in `fixtures/mineru/` | Indexed `demo_4` dataset |
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
| [`docs/architecture.md`](docs/architecture.md) | Identity, provenance, claim contract, inject lifecycle |
| [`docs/evaluation.md`](docs/evaluation.md) | Gate 3 numbers, Gate 4 ablation, scoring |
| [`docs/testing.md`](docs/testing.md) | Test layers |
| [`docs/handoff-linux.md`](docs/handoff-linux.md) | Linux host notes |

## License

Claimprint (this repository's own code) is **Apache-2.0**; see [`LICENSE`](LICENSE). Vendored RAGFlow `docker/` is redistributed unmodified under Apache-2.0. Cite as [`CITATION.cff`](CITATION.cff).
