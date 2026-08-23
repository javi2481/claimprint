[English](evaluation.md) · **Español** · [README](../README.md) · [README ES](../README.es.md)

# Evaluación

El harness de evaluación es **re-ejecutable** desde git clone. **Scores en vivo** requieren reconstruir el stack RAGFlow local (dataset `demo_4` indexado, API keys, proveedores de modelo). El clone no trae un dataset pre-indexado.

**Los números Gate 3 y Gate 4 abajo son resultados congelados del piloto en vivo** — registrados desde runs manuales en stack local. CI (`./scripts/check.sh` + pytest) valida contratos y lógica de scoring; **no** ejecuta RAGFlow ni reproduce estos scores.

Stack piloto: RAGFlow v0.26.4, MinerU `pipeline`, Infinity, Voyage, Mistral `mistral-small-latest`, umbral de similitud **0.2**, rerank on, corpus `demo_4` (10/10 docs).

## Dos pilotos (no un solo "RAG accuracy")

**Experimento 1 — Retrieval (sin claims).** ¿El stack recupera el PDF+página correcto?  
Métricas: Recall@5 / Recall@10 / MRR. Piloto chico (n=20), no benchmark IR general.

**Experimento 2 — Generación con claims (después de `push_claims`).** ¿El chat responde cuando hay claims verificados inyectados?  
Métricas: `answer_value_match`, `citation_doc_match`, `evidence_doc_match`, `abstention_correct` sobre n=10 casos task-specific. Nunca reportar como "RAG accuracy 100%".

- **answer_value_match**: contención exacta de valor (dígitos esperados aparecen en la respuesta); en casos abstención, también exige no filtrar valores prohibidos.
- **abstention_correct**: simétrico — `1` iff `abstained == expected_abstain` (checks de leak/valor son separados).
- promedios evidence/citation omiten casos solo-abstención.

## Gate 3 — números congelados del piloto en vivo

Solo retrieval (n=20; sin inject de claims):

| Arm | Recall@5 | Recall@10 | MRR |
|-------|----------|-----------|-----|
| keyword | 0.35 | 0.35 | 0.2042 |
| vector | 0.35 | 0.35 | 0.2042 |
| hybrid | 0.35 | 0.35 | 0.2042 |

Los tres brazos **empatan**: este piloto no muestra hybrid ganando. Recall@5 equals Recall@10 — ningún hit gold aparece entre ranks 6–10 en este set n=20. El factor limitante no es solo profundidad top-k; es la **identity trap** (número correcto, fila P&L equivocada) — el mismo caso **21.262.335 vs 21.259.769** que motivó Claimprint.

Chat claims-first (n=10, post-`push_claims`):

| Métrica | Score |
|--------|-------|
| answer_value_match | **1.0** |
| citation_doc_match | **1.0** |
| evidence_doc_match | **1.0** |
| abstention_correct | **1.0** |

La brecha entre solo-retrieval y chat claims-first es el argumento.

Infinity puntúa full-text con **BM25**. Los brazos `keyword` / `vector` / `hybrid` son knobs RAGFlow (`vector_similarity_weight` 0 / 1 / 0.3).

Dumps viven en `outputs/` (gitignored): `rag_retrieval_run.json`, `rag_chat_run.json`.

## Apéndice experimental — ablación Gate 4 inject

Scores observados sobre el mismo gold n=10 ([`evals/rag_chat_v1.json`](../evals/rag_chat_v1.json)) bajo tres configuraciones de inject. Complementario a Gate 3; no lo reemplaza.

**Ablación secuencial en vivo** sobre el mismo stack `demo_4` / `chat_demo_4`: brazos en orden (off → eval → chunks → eval → full → eval → restore full). El estado del chat se comparte entre brazos; no es diseño experimental totalmente aislado. **No inferir causalidad** desde orden de brazos o deltas de score — la tabla reporta configuración y outcome co-ocurrentes, no atribución controlada.

| Arm | `--inject-mode` | IDP chunk | IDP prompt | answer_value_match | citation / evidence | abstention_correct |
|-----|-----------------|-----------|------------|--------------------|---------------------|--------------------|
| A | `off` | off | off | **0.5** | 0.75 / 0.75 | 0.8 |
| B | `chunks` | on | off | **0.7** | 1.0 / 1.0 | 0.8 |
| C | `full` | on | on (pilot) | **1.0** | 1.0 / 1.0 | 1.0 |

Arm C coincide con el default del piloto. Los scores suben de A hacia C bajo este protocolo secuencial; ese patrón es descriptivo, no claim causal sobre chunk vs prompt aislados. Dump: `outputs/rag_ablation.json`.

```bash
python scripts/push_claims.py --inject-mode full   # restore pilot default
python scripts/rag_ablation.py                   # → outputs/rag_ablation.json
python scripts/clear_chat_sessions.py              # optional: drop UI sessions after long runs
```

## Catálogo de evaluación

Cuatro capas: files → identity → inject mock → live RAG. Contratos en [`evals/`](../evals/):

- [`identity_v1.json`](../evals/identity_v1.json), [`identity_v2.json`](../evals/identity_v2.json)
- [`press_v1.json`](../evals/press_v1.json), [`presentation_v1.json`](../evals/presentation_v1.json)
- [`retrieval_v1.json`](../evals/retrieval_v1.json), [`rag_chat_v1.json`](../evals/rag_chat_v1.json)

Identity traps cubiertas: interés controlante no especificado defaultea a consolidado; net income o tax **desde press/presentation** abstiene; EBITDA desde presentation; margen LTM en press y presentation; YPF / annual report abstiene.
