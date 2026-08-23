# Claimprint

**English** · [Español](README.es.md)

**Verified-claims engine for financial filings — first instance: BYMA.**  
**Rule: no claim, no answer.**

## The problem

In a BYMA quarterly filing, "resultado neto 1T26" has two neighboring P&L rows. A RAG stack can retrieve the correct page and still answer with the wrong one.

| | Value |
|--|--|
| Question | ¿Cuál es el resultado neto del período 1T26? |
| Wrong neighbor (controlante) | 21259769 |
| Claimprint (consolidado) | **21262335** |

It is row identity — *consolidado* vs *controlante*, two figures on the same page with similar magnitudes. For an analyst, an auditor, or a compliance team automating extraction over filings, that mismatch invalidates every model built on top of an answer that looks right.

### Example: one analyst workflow

1. An equity analyst building a 1T26 model asks for *resultado neto 1T26*.
2. A generic RAG stack returns **21.259.769** (controlante) — plausible, wrong scope.
3. Claimprint returns **21.262.335** with provenance: page 4, RESULTADO NETO DEL PERÍODO, `BYMA|2026-03-31|consolidado|resultado_neto`.
4. The analyst drops the figure into the model with a footnote tied to the filing.

Claimprint resolves **claim identity** — the composite key `issuer · period · scope · metric` — before any answer is generated.

This architecture was born from a specific failure: a RAG stack retrieving the correct BYMA page but confidently outputting the *controlante* row instead of the *consolidado* row. Claimprint formalizes the fix: resolve identity as a typed claim before generation.

[`scripts/idp_ask.py`](scripts/idp_ask.py) answers the consolidated row from committed fixtures — no Docker, no API keys. See [Quick start](#quick-start).

## Who this is for

| Role | Context | What they get |
|------|---------|----------------|
| Research / equity analyst | Building models on financial statements, press releases, presentations | Figures with verified identity (consolidado vs controlante) |
| Auditor / controller | Reviewing automated extraction | Abstention when a question has no claim (no claim, no answer) |
| IDP / RAG engineer | Designing document → answer pipelines | Clear separation: claim = source of truth, chunk = derived input for chat |
| Compliance / risk | Automating over regulated filings | Provenance (page, row, filing) on every answer |

## Why not just use X?

- **Better RAG / hybrid search?** The identity trap is structural — same page, two neighboring rows. In the BYMA pilot, keyword, vector, and hybrid retrieval **tie** at Recall@5 **0.35** / MRR **0.2042** (n=20).
- **GPT-4 + prompt engineering?** Prompt tuning does not guarantee structural abstention. Claimprint abstains when no verified claim exists.
- **Batch extractors (Unstract, Nanonets, …)?** Strong on field extraction; weak on scope disambiguation (*consolidado* vs *controlante*) without typed identity.
- **Fine-tuned embeddings?** Neighboring P&L rows share semantic context; embeddings do not encode accounting scope.

Methodology and frozen scores: [`docs/evaluation.md`](docs/evaluation.md).

## How Claimprint works

Claimprint is a **verified-claims engine**, not a RAG wrapper. A document enters document intelligence (parse with MinerU, classify, extract) and becomes a **typed claim**: a structured figure with **identity** (`issuer · period · scope · metric`), **value**, and **provenance** (page, row, filing). The composite identity is resolved and verified before any answer is emitted. The primary path is **exact lookup** → verified answer. RAG chat is an **optional** layer that consumes verified claims; it is not the source of truth. If no claim passes verification, Claimprint **abstains** — no claim, no answer.

![Claimprint architecture — document to verified claim](docs/assets/claimprint-architecture.png)

```text
PDF → MinerU → Recipe → Claim → [optional RAG chunk] → Chat
                      ↑ source of truth
```

| Artifact | Role |
|----------|------|
| PDF | primary evidence |
| MinerU fixture | parsed representation |
| Recipe | extraction contract |
| Eval gold | test expectation |
| Claim | operational source of truth |
| RAG chunk | derived input for chat |
| Chat | consumer |

**Core concepts:** a **typed claim** is the verified figure (composite identity + value + provenance). A **recipe** is the extraction contract for a document class (e.g. [`recipes/financial_statement.json`](recipes/financial_statement.json)). A **projector** maps extracted rows onto that schema — resolving **scope** (consolidado vs controlante) along the way.

Details: [`docs/architecture.md`](docs/architecture.md)

## What the pilot proves

The **21.262.335 vs 21.259.769** trap was reproduced in a controlled BYMA pilot (n=20 retrieval / n=10 chat).

If retrieval alone — keyword, vector, or hybrid — could resolve the identity trap, this architecture would not be needed. Over the same corpus, the three retrieval arms **tie** at Recall@5 **0.35** / MRR **0.2042** — recovering the right PDF page is not enough when two neighboring rows share semantic context.

![Retrieval-only vs claims-first — identity trap](docs/assets/claimprint-retrieval-vs-chat.png)

With claims injected (`push_claims`), the system answered with the correct value **10/10**, cited the right document **10/10**, matched evidence **10/10**, and abstained correctly when it should **10/10** (`answer_value_match`, `citation_doc_match`, `evidence_doc_match`, `abstention_correct` on n=10 task-specific cases). The jump is not better retrieval — it is identity resolved before generation.

Frozen live-pilot results from a local RAGFlow stack. Full methodology, Gate 4 ablation, and scoring definitions: [`docs/evaluation.md`](docs/evaluation.md).

## What the clone includes

| Out of the box (no Docker) | Optional (you build locally) |
|----------------------------|------------------------------|
| BYMA PDFs + MinerU fixtures in [`fixtures/mineru/`](fixtures/mineru/) | RAGFlow stack via [`scripts/up.sh`](scripts/up.sh) |
| [`scripts/idp_ask.py`](scripts/idp_ask.py) — financial statements, press, presentation | Dataset **`demo_4`** indexed in the UI (not shipped in git) |
| Recipes, [`evals/`](evals/), pytest, [`scripts/check.sh`](scripts/check.sh) | Chat pilot + frozen metrics in [`docs/evaluation.md`](docs/evaluation.md) |
| Human review (HITL) [`scripts/review_pack.py`](scripts/review_pack.py), dossier [`scripts/informe.py`](scripts/informe.py) | API keys in `.env` (Mistral + Voyage; gitignored) |

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
python scripts/review_pack.py   # outputs/review/index.html (human review / HITL)
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
| `scripts/idp_ask.py`, human review (HITL), dossier | Pre-built RAG chunks or chat |

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

**Status:** v1.0 — kernel validated on BYMA financial statements. Not yet generalizable to other issuers or document types.

Claimprint shows that document AI over financial filings fails at **identity**, not at retrieval depth or embedding quality — the same **21.262.335 vs 21.259.769** trap that motivated this project. The BYMA instance is frozen and reproducible: recipes, evals, abstention, optional RAGFlow UI.

### Next milestones

1. **Audit-grade provenance** — bbox-level evidence for compliance traceability
2. **Cross-document guardrails** — prevent chat from mixing deck figures with financial statements
3. **Second document class** — validate recipe/projector beyond BYMA finance
4. **API layer** (exploratory) — identity lookup without local Python setup

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Repository health

[![CI](https://github.com/javi2481/claimprint/actions/workflows/ci.yml/badge.svg)](https://github.com/javi2481/claimprint/actions/workflows/ci.yml)

CI runs `./scripts/check.sh` and pytest — contract and scoring logic, not live RAGFlow pilot scores.

## License

Claimprint (this repository's own code) is **Apache-2.0**; see [`LICENSE`](LICENSE). Vendored RAGFlow `docker/` is redistributed unmodified under Apache-2.0. Cite as [`CITATION.cff`](CITATION.cff).
