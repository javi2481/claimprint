# OpenSpec / Claimprint (hybrid)

> **OpenSpec is design history / implementation record.** Operational narrative SoT is the root `README.md`.


Claimprint usa SDD **hybrid**: archivos en `openspec/` + observaciones Engram (`project: claimprint`).

## Quick path

1. **Sin change activo de producto** — v1.0.0 shipped (Phase 0 + WP-1/2/3 archivados).
2. Archivado reciente: [`claimprint-v1.1-three-wp`](changes/archive/claimprint-v1.1-three-wp/) (período content-first, ablation, MinerU provenance).
3. Cerrado: [`claimprint-v1-close`](changes/claimprint-v1-close/) (v1.0.0 release gate).
4. IDP en cualquier PC: `./scripts/check.sh`. Compose en ≥16 GB. Tras merge en la UI: `python scripts/push_claims.py` y chat nuevo.

## Details

| Tema | Valor |
|------|--------|
| Producto | Claimprint — claims intelligence; instancia BYMA (`docs/archivos_muestra/`) |
| UI | RAGFlow v0.26.4 + Infinity + MinerU + Voyage + Mistral (SoT vivo = README / v1.0.0) |
| Tests | `./scripts/check.sh` (pytest identidad). Chat live no es el DoD del IDP |
| Persistencia | `openspec/config.yaml` → `persistence: hybrid` |

## Checklist

- [x] Change post-v1 archivado (`claimprint-v1.1-three-wp`)
- [ ] `claimprint-ragflow` sigue siendo el pin de UI/stack (sin trabajo IDP adentro)
- [ ] `.env` y API keys **no** están en git

## Next step

Quick start: [`README.md`](../README.md) en la raíz del repo.
