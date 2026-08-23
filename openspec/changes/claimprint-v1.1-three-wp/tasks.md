# Tasks: claimprint-v1.1-three-wp

## Phase 0 — MinerU export (unblocks WP-1 + WP-3)

- [x] 0.1 `schemas/mineru_artifact.py`: load `content.json` sidecar; normalize bbox 0–1
- [x] 0.2 `export_mineru.py --with-content --content-only`: write `fixtures/mineru/{stem}.content.json`
- [x] 0.3 Commit sidecars for all `docs/archivos_muestra/*.pdf` in demo_4
- [x] 0.4 `fixtures/mineru/README.md`: document `.md` + `.content.json` contract
- [x] 0.5 Gate 0: `./scripts/check.sh` green (no Docker required)

## WP-1 — Content-first período

- [x] 1.1 `press_release.py` + `results_presentation.py`: text-before-filename period
- [x] 1.2 Use `front_matter` / portada blocks for period when sidecar exists
- [x] 1.3 Fix or extend gold only where filename-first was wrong (none needed)
- [x] 1.4 Tests: `test_period_resolve.py`; press/presentation evals green
- [x] 1.5 Gate 5: README — period resolution order documented

## WP-2 — Ablation prompt vs claim

- [x] 2.1 `push_claims.py`: `--inject-mode {off,chunks,full}`
- [x] 2.2 Restore procedure: ablation ends with `inject_mode=full` (no clone chats)
- [x] 2.3 `scripts/rag_ablation.py`: gold × 3 arms → `outputs/rag_ablation.json`
- [x] 2.4 README table A/B/C (Gate 4 section); Gate 3 frozen lines untouched
- [x] 2.5 Gate 4: `rag_ablation.py` + `clear_chat_sessions.py` documented in README

## WP-3 — Provenance / bbox (MinerU)

- [x] 3.1 `Claim.document_id` + `Claim.source_bbox` optional fields
- [x] 3.2 `match_bbox(source_text, page, content.json)` helper
- [x] 3.3 Wire EEFF + press + presentation projectors (best-effort bbox)
- [x] 3.4 `review_pack.py`: show bbox + page when present
- [x] 3.5 Gate 6: EEFF 1T26 neto consolidado has bbox or honest null (pytest)

## Ship

- [x] Tag `v1.0.0` when WP-1 + Phase 0 done (WP-2 ablation + WP-3 bbox may follow in same minor line)
- [x] WP-3 bbox gate — pytest + review_pack highlight
