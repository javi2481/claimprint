# OpenSpec / Claimprint (hybrid)

> **OpenSpec is design history / implementation record.** Operational narrative SoT is the root `README.md`.


Claimprint usa SDD **hybrid**: archivos en `openspec/` + observaciones Engram (`project: claimprint`).

## Quick path

1. Change **activo:** [`claimprint-v1-close`](changes/claimprint-v1-close/).
2. Shipped: [`claimprint-idp-kernel`](changes/claimprint-idp-kernel/), [`claimprint-finance-pnl-claims`](changes/claimprint-finance-pnl-claims/), [`claimprint-claim-store`](changes/claimprint-claim-store/), [`claimprint-press-release`](changes/claimprint-press-release/), [`claimprint-mineru-parse`](changes/claimprint-mineru-parse/), [`claimprint-product-shape`](changes/claimprint-product-shape/), [`claimprint-claims-to-rag`](changes/claimprint-claims-to-rag/), [`claimprint-results-presentation`](changes/claimprint-results-presentation/), [`claimprint-academic-close`](changes/claimprint-academic-close/), [`claimprint-press-ltm`](changes/claimprint-press-ltm/). Pin UI/stack: [`claimprint-ragflow`](changes/claimprint-ragflow/) — no inflar.
3. IDP en cualquier PC: `./scripts/check.sh`. Compose en ≥16 GB. Tras merge en la UI: `python scripts/push_claims.py` y chat nuevo.

## Details

| Tema | Valor |
|------|--------|
| Producto | Claimprint — claims intelligence; instancia BYMA (`docs/archivos_muestra/`) |
| UI | RAGFlow v0.26.4 + Infinity + MinerU + Voyage + Mistral (SoT vivo = README / v1.0.0) |
| Tests | `./scripts/check.sh` (pytest identidad). Chat live no es el DoD del IDP |
| Persistencia | `openspec/config.yaml` → `persistence: hybrid` |

## Checklist

- [ ] Este archivo nombra el change activo (`claimprint-v1-close`)
- [ ] `claimprint-ragflow` sigue siendo el pin de UI/stack (sin trabajo IDP adentro)
- [ ] `.env` y API keys **no** están en git

## Next step

Quick start: [`README.md`](../README.md) en la raíz del repo.
