# MinerU parse artifacts

Texto durable del parse MinerU (un archivo por PDF de `docs/archivos_muestra/`). El kernel clasifica y extrae **solo** desde acá.

## Files per PDF

| File | Role |
|------|------|
| `{stem}.md` | Page-marked text (`<!-- page: N -->`). IDP extractors read this. |
| `{stem}.content.json` | Span sidecar: text + bbox + page (Phase 0+). |

Loader: `schemas/mineru_artifact.py` → `load_content_sidecar(pdf)`.

## Quick path

1. Texto (no pisa si ya existe el sidecar):

```bash
python scripts/export_mineru.py
```

2. Sidecars bbox **sin tocar** los `.md` commiteados (MinerU API primero si está arriba; si no, posiciones RAGFlow):

```bash
python scripts/export_mineru.py --with-content --content-only
```

Solo MinerU API (sin RAGFlow; no toca `.md`):

```bash
python scripts/export_mineru.py --mineru-api-only
```

Forzar solo RAGFlow (offline / CI path commiteado):

```bash
python scripts/export_mineru.py --with-content --content-only --ragflow-content-only
```

3. Opcional fino vía `mineru-api` `content_list` explícito:

```bash
python scripts/export_mineru.py --with-content --content-only --prefer-mineru-api
```

4. Sin RAGFlow: `python scripts/export_mineru.py --bootstrap-layout` (solo `.md`, sin bbox).

5. `./scripts/check.sh`

**Importante:** no re-exportar `.md` desde RAGFlow si cambió el chunking — rompe page markers y evals. Usar `--content-only` para refrescar bbox.

No recortar memorias: un parse completo.
