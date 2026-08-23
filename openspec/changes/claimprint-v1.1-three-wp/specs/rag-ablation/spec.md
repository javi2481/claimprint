# Spec delta: rag-ablation

## Requirement: Three-arm ablation on fixed gold

The repository MUST provide a script that scores `evals/rag_chat_v1.json` under three inject
configurations without mutating Gate 3 published totals.

| Arm | Chunk inject | IDP prompt rules |
|-----|--------------|------------------|
| A | off | off |
| B | on | off |
| C | on | on |

### Scenario: Ablation output is separable

- WHEN `rag_ablation.py` completes
- THEN it MUST write per-arm summaries using `rag_chat_score` keys
- AND MUST NOT overwrite `outputs/rag_chat_run.json` from Gate 3 without `--force`
