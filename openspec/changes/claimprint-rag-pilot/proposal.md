# Proposal: RAG retrieval pilot (qrels + skip harness)

> **Change activo (producto).** No inflar kernel, plugins, academic-close, press-ltm, ni el pin [`claimprint-ragflow`](../claimprint-ragflow/). Do not fatten [`scripts/push_claims.py`](../../../scripts/push_claims.py).

## Intent

Identity evals already prove exact-match claims. The chat stack (Infinity + Voyage + Mistral) has no committed retrieval gold. Claimprint MUST add a small pilot: 20 page-qrels, 10 chat cases, metric helpers, and scripts that skip without RAGFlow — so the thesis can measure keyword vs vector vs hybrid **after** a desktop run, without inventing Recall numbers in CI.

## Scope

### In Scope

- `evals/retrieval_v1.json` (20 qrels: PDF + page)
- `evals/rag_chat_v1.json` (10 cases: 4 identity, 3 narrative, 2 abstain, 1 comparison)
- Pure `recall_at_k` / `mrr`; pytest without HTTP
- `retrieval_bench.py` + `rag_eval.py`: exit 0 + skip without stack
- README architecture (hybrid keyword + vector; no Okapi BM25; metrics table with em dash)

### Out of Scope

Whoosh, Okapi, RRF claims, RAPTOR/KG, fake 0.91 table, pytest that calls RAGFlow, inject rewrite, transcript/memoria extract

## Capabilities

### New Capabilities

- `retrieval-pilot`: Page-level qrels and three-arm bench (weights 0 / 1 / 0.3), rerank off.
- `rag-chat-pilot`: Ten chat cases scored after `push_claims`.

### Modified Capabilities

None of the identity harnesses. `check.sh` only adds file contracts.

## Approach

Gold is `doc` + `page`, not `identity_key`. Live retrieval uses the same API/token pattern as `push_claims.py`. CI never requires Docker.

## Rollback Plan

Delete this change folder, new evals/examples/scripts/schema, restore README pointers.

## Success Criteria

- [x] `./scripts/check.sh` green without RAGFlow
- [x] Bench/eval skip with `no_ragflow`
- [x] README does not publish invented Recall numbers
- [x] Identity pytest still does not import RAGFlow

Desktop run (historical, first pilot): retrieval arms Recall@5/10 0.25 / MRR 0.125; chat scores 0.7 / 0.6 / 0.7 / 0.7.
**Live SoT (v1.0.0):** README — Recall@5 **0.35** / MRR **0.2042**; chat answer_value_match/citation_doc_match/evidence_doc_match/abstention_correct **1.0**; chat LLM **Mistral** `mistral-small-latest`. (Gate-3 remeasure after page-hit honesty fix.)
