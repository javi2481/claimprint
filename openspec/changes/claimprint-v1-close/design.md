# Design: claimprint-v1-close

## Release gate

A+B block v1.0.0. Numbers change once at Gate 3 after remeasure.
C/D block only on correctness regressions. E is narrative close.

## ADR: inject scope

`push_claims` resolves dataset `demo_4` and chat `chat_demo_4` by name (CLI/env overrides).
Missing target → non-zero exit. No other dataset/chat is mutated.

## ADR: chat metric names

| Old key | New key | Meaning |
|---------|---------|---------|
| retrieval | evidence_doc_match | cited expected PDF (not Recall@page) |
| answer | answer_value_match | exact-value containment |
| citation | citation_doc_match | expected doc, not sidecar |
| abstention | abstention_correct | expected_abstain == actual |

## ADR: retrieval hits without page

`chunk_to_hit` returns `None` when page cannot be resolved. Unknown page ≠ page 1.

## ADR: provenance (doc only)

CURRENT identity: issuer, period, scope, metric.
CURRENT provenance: source_page, source_text.
FUTURE: document_id, source_hash, bbox/region.

## ADR: narrative SoT

README = what exists / measured / numbers mean. evals/ = gold. OpenSpec = history. LinkedIn ⊆ README.
