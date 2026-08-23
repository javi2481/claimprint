**English** · [Español](README.es.md) · [README](../../README.md) · [README ES](../../README.es.md)

# Sample files (BYMA)

Real BYMA PDFs. **One MinerU parse**, two layers: IDP reads `fixtures/mineru/<stem>.md`; RAGFlow uses UI dataset **`demo_4`**.

The git clone ships the artifacts. A clone does **not** ship Docker volumes.

Demo order: **configure the dataset** (MinerU, Spanish, KG/RAPTOR off) → **upload** → for each file set **Task size per page = 128** → **Parse** one at a time → `python scripts/export_mineru.py` to overwrite fixtures.

Do not enable Knowledge graph or RAPTOR: they are not parsers and consume chat tokens.

Optional stack details: **Optional RAGFlow UI** section in the root [README](../../README.md) (chat demo: Mistral + Voyage, threshold 0.2, then `push_claims`).

## Parse order

1. Press releases and transcript (few pages).
2. Presentations.
3. Financial statements (tables; slow on CPU).
4. Annual reports (~190 pages; last).

Do not reuse `demo_3` or files already parsed with DeepDoc/Naive: **new dataset**, re-upload after setting MinerU in Settings. Changing the dataset dropdown does not rewrite each file's parser or chunks.
