# Evaluation

The evaluation harness is **re-runnable** from git clone. **Live scores** require rebuilding the local RAGFlow stack (indexed `demo_4`, API keys, model providers). The clone does not ship a pre-indexed dataset.

**Gate 3 and Gate 4 numbers below are frozen live-pilot results** — recorded from manual runs on a local stack. CI (`./scripts/check.sh` + pytest) validates contracts and scoring logic; it does **not** execute RAGFlow or reproduce these scores.

Pilot stack: RAGFlow v0.26.4, MinerU `pipeline`, Infinity, Voyage, Mistral `mistral-small-latest`, similarity threshold **0.2**, rerank on, corpus `demo_4` (10/10 docs).

## Two pilots (not one "RAG accuracy")

**Experiment 1 — Retrieval (no claims).** Can the stack recover the right PDF+page?  
Metrics: Recall@5 / Recall@10 / MRR. Small pilot (n=20), not a general IR benchmark.

**Experiment 2 — Claim-grounded generation (after `push_claims`).** Can chat answer when verified claims are injected?  
Metrics: `answer_value_match`, `citation_doc_match`, `evidence_doc_match`, `abstention_correct` on n=10 task-specific cases. Never reported as "RAG accuracy 100%".

- **answer_value_match**: exact-value containment (expected digits appear in reply); on abstain cases, also requires no forbidden-value leak.
- **abstention_correct**: symmetric — `1` iff `abstained == expected_abstain` (leak/value checks are separate).
- evidence/citation averages skip abstain-only cases.

## Gate 3 — frozen live-pilot numbers

Retrieval-only (n=20; no claim inject):

| Arm | Recall@5 | Recall@10 | MRR |
|-------|----------|-----------|-----|
| keyword | 0.35 | 0.35 | 0.2042 |
| vector | 0.35 | 0.35 | 0.2042 |
| hybrid | 0.35 | 0.35 | 0.2042 |

The three arms **tie**: this pilot does not show hybrid winning. Recall@5 equals Recall@10 — no gold hit appears between ranks 6–10 in this n=20 set. The limiting factor is not simply top-k depth; it is the **identity trap** (correct number, wrong P&L row).

Claims-first chat (n=10, post-`push_claims`):

| Metric | Score |
|--------|-------|
| answer_value_match | **1.0** |
| citation_doc_match | **1.0** |
| evidence_doc_match | **1.0** |
| abstention_correct | **1.0** |

The gap between retrieval-only and claims-first chat is the argument.

Infinity scores full-text with **BM25**. The `keyword` / `vector` / `hybrid` arms are RAGFlow knobs (`vector_similarity_weight` 0 / 1 / 0.3).

Dumps live in `outputs/` (gitignored): `rag_retrieval_run.json`, `rag_chat_run.json`.

## Experimental appendix — Gate 4 inject ablation

Observed scores on the same n=10 gold ([`evals/rag_chat_v1.json`](../evals/rag_chat_v1.json)) under three inject configurations. Complementary to Gate 3; does not replace it.

**Live sequential ablation** over the same `demo_4` / `chat_demo_4` stack: arms run in order (off → eval → chunks → eval → full → eval → restore full). Chat state is shared across arms; this is not a fully isolated experimental design. **Do not infer causality** from arm ordering or score deltas — the table reports co-occurring configuration and outcome, not controlled attribution.

| Arm | `--inject-mode` | IDP chunk | IDP prompt | answer_value_match | citation / evidence | abstention_correct |
|-----|-----------------|-----------|------------|--------------------|---------------------|--------------------|
| A | `off` | off | off | **0.5** | 0.75 / 0.75 | 0.8 |
| B | `chunks` | on | off | **0.7** | 1.0 / 1.0 | 0.8 |
| C | `full` | on | on (pilot) | **1.0** | 1.0 / 1.0 | 1.0 |

Arm C matches the pilot default. Scores rise from A toward C under this sequential protocol; that pattern is descriptive, not a causal claim about chunk vs prompt in isolation. Dump: `outputs/rag_ablation.json`.

```bash
python scripts/push_claims.py --inject-mode full   # restore pilot default
python scripts/rag_ablation.py                   # → outputs/rag_ablation.json
python scripts/clear_chat_sessions.py              # optional: drop UI sessions after long runs
```

## Evaluation catalog

Four layers: files → identity → inject mock → live RAG. Contracts in [`evals/`](../evals/):

- [`identity_v1.json`](../evals/identity_v1.json), [`identity_v2.json`](../evals/identity_v2.json)
- [`press_v1.json`](../evals/press_v1.json), [`presentation_v1.json`](../evals/presentation_v1.json)
- [`retrieval_v1.json`](../evals/retrieval_v1.json), [`rag_chat_v1.json`](../evals/rag_chat_v1.json)

Identity traps covered: unspecified controlling interest defaults to consolidated; net income or tax **from press/presentation** abstains; EBITDA from presentation; LTM margin in press and presentation; YPF / annual report abstains.
