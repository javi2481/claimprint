# Tasks: Claimprint RAGFlow local stack

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~350–500 authored; vendor `docker/` pin likely >400 total |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | Single PR (`size:exception`; vendor pin + no PR split) |
| Delivery strategy | auto-chain |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Vendor pin, overlay OCR, up.sh, fixtures, README | single (`size:exception`) | `test -f vendor/PIN.md && test -f docker-compose.overlay.yml && test -f scripts/up.sh && ls docs/archivos_muestra/*.pdf` | `scripts/up.sh`; `docker compose ps`; README E2E. N/A if no Docker or RAM <16 GB | `vendor/`, `docker-compose.overlay.yml`, `docker/paddleocr/`, `.env.example`, `scripts/up.sh`, `README.md`, `docs/archivos_muestra/`, `.gitignore` |

## Phase 1: Vendor pin and ignores

- [x] 1.1 Copy official `infiniflow/ragflow` `docker/` **v0.26.4** into `vendor/ragflow-docker/` (Apache-2.0); do not edit upstream.
- [x] 1.2 Create `vendor/PIN.md` with tag `v0.26.4`, source URL, and do-not-edit-upstream.
- [x] 1.3 Modify `.gitignore`: keep ignoring root `.env`; ignore `vendor/ragflow-docker/.env`, `ragflow-logs/`, and compose volumes.

## Phase 2: Overlay, OCR image, env

- [x] 2.1 Create `docker/paddleocr/Dockerfile` CPU serve: `paddlex --serve --pipeline PP-StructureV3 --device cpu --host 0.0.0.0 --port 8080` (`POST /layout-parsing`); pin PaddlePaddle 3.x + `paddlex[serving]`.
- [x] 2.2 Create `docker-compose.overlay.yml`: `paddleocr` on network `ragflow`; `build: ./docker/paddleocr`; do **not** publish host `:8080`.
- [x] 2.3 Create `.env.example`: `DOC_ENGINE=infinity`, `COMPOSE_PROFILES=infinity,cpu`, `RAGFLOW_IMAGE=infiniflow/ragflow:v0.26.4`, `PADDLEOCR_API_URL=http://paddleocr:8080/layout-parsing`, PP-StructureV3, no AI Studio token; Ollama `http://host.docker.internal:11434` (never `127.0.0.1`).

## Phase 3: Startup script

- [x] 3.1 Create `scripts/up.sh`: read-only check `vm.max_map_count` ≥ 262144; warn/fail if low and do not claim ready; no `eval` of user strings; no `sysctl -w` unless README documents it.
- [x] 3.2 In `scripts/up.sh`: sync `.env` → `vendor/ragflow-docker/.env`; `docker compose --env-file .env -f vendor/ragflow-docker/docker-compose.yml -f docker-compose.overlay.yml up -d`; document/run `ollama pull qwen2.5:1.5b` and `bge-m3` with `OLLAMA_HOST=0.0.0.0`.

## Phase 4: BYMA sample PDFs

- [x] 4.1 Place BYMA sample PDFs in `docs/archivos_muestra/` covering comunicados, EEFF, presentaciones, and memoria.

## Phase 5: README, negative scope, verify

- [x] 5.1 Create Spanish `README.md`: x86_64, ≥16 GB, Docker ≥24, Compose ≥v2.26.1, not ARM64; `OLLAMA_HOST=0.0.0.0`; Spanish UI; non-blank Spanish Empty response; Show Quote; BYMA samples; first-run KB/chat.
- [x] 5.2 Add README E2E: ingest BYMA PDFs via MinerU; in-corpus Spanish + Show Quote; out-of-corpus Spanish Empty (no invention); parser down → visible ingest fail, no fabricated text.
- [x] 5.3 Confirm no `app.py`, `ledger_lens/`, Gradio, HF Space, Compose Ollama, TEI, or Elasticsearch.
- [x] 5.4 Verify: compose healthy (UI `:80`) on ≥16 GB. Manual E2E per README. Host <16 GB: `scripts/check.sh` only. Skip full smoke if no Docker Compose.
- [x] 5.5 Add `scripts/check.sh` (contracts, `pdftotext` fixtures, host probe) and `docs/agenda/` for deferred Parallel items.

## Phase 6: extra chat proxy (rolled back 2026-08-16) — historical

- [x] 6.1 Tried a Compose chat proxy hop; not useful for this demo (RAGFlow already talks to chat LLM / Ollama / Voyage in Model providers).
- [x] 6.2 Rolled back the overlay and agenda note the same day.
- [x] 6.3 Chat went Gemini factory then **Groq** `llama-3.3-70b-versatile` (historical `chat_demo_4`). OpenRouter Nano `:free` is not the default. Voyage stays native.

## Phase 7: Groq chat default (2026-08-16) — historical

- [x] 7.1 Align README, `.env.example`, `scripts/check.sh` / `up.sh`, agenda, research index, and OpenSpec local-stack/portfolio-local to Groq `llama-3.3-70b-versatile` (instance `demo_4`). Do not document Gemini flash-lite or OpenRouter Nano `:free` as the running default.
  - **Superseded by Phase 8:** live default is Mistral (README / v1.0.0).

## Phase 8: Mistral live default (2026-08-22)

- [x] 8.1 Align README, `.env.example`, `scripts/check.sh` / `up.sh`, `vendor/PIN.md`, and OpenSpec local-stack/portfolio-local to Mistral `mistral-small-latest` (instance `demo_4`, chat thr **0.2**). Do not document Groq, Gemini flash-lite, or OpenRouter Nano `:free` as the running default.
- [x] 8.2 Confirm live SoT metrics stay in README: retrieval Recall@5 **0.35** / MRR **0.2042**; claims-first chat **1.0** (n=20 / n=10).
