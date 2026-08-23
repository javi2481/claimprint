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

- [ ] 2.1 `push_claims.py` flags: `--chunks-only`, `--no-prompt`, `--off` (names TBD)
- [ ] 2.2 Optional: clone chats `chat_demo_4_a/b/c` or documented restore procedure
- [ ] 2.3 `scripts/rag_ablation.py`: run gold × 3 arms → `outputs/rag_ablation.json`
- [ ] 2.4 README table A/B/C (new section); **do not** change Gate 3 frozen lines
- [ ] 2.5 Gate 4: one command + Docker; `clear_chat_sessions.py` documented in flow

## WP-3 — Provenance / bbox (MinerU)

- [ ] 3.1 `Claim.document_id` + `Claim.source_bbox` optional fields
- [ ] 3.2 `match_bbox(source_text, page, content.json)` helper
- [ ] 3.3 Wire EEFF + press + presentation projectors (best-effort bbox)
- [ ] 3.4 `review_pack.py`: show bbox + page when present
- [ ] 3.5 Gate 6: spot-check EEFF 1T26 neto consolidado visually; abstain if no match

## Ship

- [ ] Tag `v1.1.0` when WP-1 + Phase 0 done (bbox/ablation may follow in v1.2)
- [ ] Or single tag `v1.1.0` when all three gates pass — decide at Gate 5 review
