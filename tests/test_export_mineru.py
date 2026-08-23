"""export_mineru content sidecar source priority."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import export_mineru  # noqa: E402
from schemas.mineru_artifact import BBOX_MINERU_1000  # noqa: E402


def test_write_content_prefers_mineru_api(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")
    blocks = [
        {"type": "text", "text": "linea", "bbox": [0, 0, 1000, 100], "page_idx": 0},
    ]
    chunks = [{"content": "chunk", "positions": [[1, 0, 100, 0, 50]]}]
    fixtures = tmp_path / "mineru"

    with patch.object(export_mineru, "mineru_reachable", return_value=True):
        with patch.object(export_mineru, "content_list_from_mineru", return_value=blocks):
            dest = export_mineru.write_content_for_pdf(
                pdf, chunks, prefer_mineru=True, fixtures=fixtures
            )
    assert dest is not None
    sidecar = dest.read_text(encoding="utf-8")
    assert "mineru_api" in sidecar
    assert BBOX_MINERU_1000 in sidecar


def test_write_content_falls_back_to_ragflow(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")
    chunks = [{"content": "chunk", "positions": [[1, 0, 100, 0, 50]]}]

    with patch.object(export_mineru, "mineru_reachable", return_value=False):
        dest = export_mineru.write_content_for_pdf(
            pdf, chunks, prefer_mineru=True, fixtures=tmp_path / "mineru"
        )
    assert dest is not None
    assert "ragflow_chunks" in dest.read_text(encoding="utf-8")
