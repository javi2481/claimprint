# Proposal: claimprint-v1.1-three-wp

## Intent

Post-v1.0.0 work in three simple tracks: better period extraction, honest ablation of
inject vs prompt, and MinerU-backed provenance (bbox). Gate 3 pilot numbers stay frozen
on v1.0.0 unless a scoring bug is found.

## In scope

### WP-1 — Content-first período
Infer press/presentation period from MinerU text (portada / content_list) before filename.
Filename remains fallback only.

### WP-2 — Ablation prompt vs claim
Three reproducible chat arms on `evals/rag_chat_v1.json`: no inject, chunk-only, full IDP.
Publish comparison table; do not overwrite v1.0.0 Gate 3 numbers.

### WP-3 — Provenance via MinerU (bbox first)
Stop discarding MinerU richness at export. Attach optional `source_bbox` + `document_id`
to claims when a text span match exists; no invented geometry.

### Cross-cutting — MinerU export
Extend `export_mineru.py` to persist `content_list` (and optionally `middle_json` slice)
alongside `fixtures/mineru/*.md`. WP-1 and WP-3 depend on this.

## Out of scope

- Retagging v1.0.0 pilot metrics without a new gate label (v1.1+ only)
- Paddle as primary parser (optional cross-check later)
- Legal vertical, custom UI, prompt tuning for glamour
- LinkedIn polish (shipped separately)

## Rollback

Revert export sidecars and extractor order; claims without bbox remain valid.
Ablation uses separate chat names or restore-from-backup inject state.
