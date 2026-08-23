"""Tests for MinerU content sidecars."""

from __future__ import annotations

import json
from pathlib import Path

from schemas.mineru_artifact import (
    BBOX_MINERU_1000,
    BBOX_RAGFLOW_PAGE,
    ContentSidecar,
    content_path,
    load_content_sidecar,
    spans_from_content_list,
    spans_from_ragflow_chunks,
    write_content_sidecar,
)


def test_spans_from_content_list_normalizes_bbox() -> None:
    sidecar = spans_from_content_list(
        [
            {
                "type": "text",
                "text": "BYMA anuncia resultados",
                "bbox": [100, 200, 900, 300],
                "page_idx": 0,
            }
        ],
        pdf_name="press.pdf",
    )
    assert sidecar.source == "mineru_api"
    assert len(sidecar.spans) == 1
    span = sidecar.spans[0]
    assert span.page == 1
    assert span.bbox_space == BBOX_MINERU_1000
    assert span.bbox_norm == (0.1, 0.2, 0.9, 0.3)


def test_spans_from_ragflow_chunks_page_norm() -> None:
    chunks = [
        {
            "content": "RESULTADO NETO DEL PERÍODO 21.262.335",
            "positions": [[4, 100, 500, 200, 240], [4, 100, 1000, 300, 800]],
        }
    ]
    sidecar = spans_from_ragflow_chunks(chunks, pdf_name="eeff.pdf")
    assert sidecar.source == "ragflow_chunks"
    assert len(sidecar.spans) == 2
    assert sidecar.spans[0].bbox_space == BBOX_RAGFLOW_PAGE
    assert sidecar.spans[0].bbox_norm[2] == 0.5
    assert sidecar.spans[1].bbox_norm[2] == 1.0


def test_write_and_load_roundtrip(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF")
    sidecar = spans_from_content_list(
        [{"type": "title", "text": "Hola", "bbox": [0, 0, 1000, 100], "page_idx": 1}],
        pdf_name=pdf.name,
    )
    dest = write_content_sidecar(pdf, sidecar, fixtures=tmp_path / "mineru")
    assert dest == content_path(pdf, fixtures=tmp_path / "mineru")
    loaded = load_content_sidecar(pdf, fixtures=tmp_path / "mineru")
    assert loaded is not None
    assert loaded.pdf_name == pdf.name
    assert loaded.spans[0].page == 2
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["version"] == "content_v1"
