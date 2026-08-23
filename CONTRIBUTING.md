# Contributing to Claimprint

Thank you for your interest in Claimprint. This project is **Apache-2.0** licensed.

## Getting started

```bash
git clone https://github.com/javi2481/claimprint.git
cd claimprint
uv venv && uv pip install -r requirements-dev.txt   # or: python -m venv .venv && pip install -r requirements-dev.txt
./scripts/check.sh
```

On Windows, run `./scripts/check.sh` from Git Bash or WSL.

## Before you open a PR

1. Run `./scripts/check.sh` — it must pass.
2. Keep changes focused; match existing style in the files you touch.
3. For claim shape, inject lifecycle, or eval contracts, read [`docs/architecture.md`](docs/architecture.md) first.
4. Do not commit secrets (`.env`, API keys, indexed RAG volumes).

## Issues and pull requests

- **Bugs:** open an issue with repro steps, expected vs actual, and `./scripts/check.sh` output if relevant.
- **Features:** describe the use case (analyst, auditor, compliance, engineer) before implementation details.
- **PRs:** link the issue when applicable; include a short summary of behavior change.

## Help wanted

Areas where contributions are especially useful:

- **Second document class** — validate recipe/projector beyond BYMA financial statements
- **Audit-grade provenance** — bbox-level evidence and HITL review improvements
- **Cross-document guardrails** — deck vs financial statement inject rules in chat
- **API layer** (exploratory) — REST identity lookup without local Python setup

## Evaluation and pilot scores

Frozen live-pilot metrics (Recall@5, chat scores) are documented in [`docs/evaluation.md`](docs/evaluation.md). CI validates contracts and scoring logic; it does **not** reproduce RAGFlow live scores.

## Code of conduct

Be direct, precise, and respectful. Disagreements belong in issues and PR review, not personal attacks.
