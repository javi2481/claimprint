"""HITL bbox overlay helpers."""

from __future__ import annotations

from pathlib import Path

from schemas.claim import METRIC_NETO, SCOPE_CONSOLIDADO, Claim, identity_key
from schemas.review import write_review_pack
from schemas.review_highlight import bbox_overlay_style, highlight_html, highlight_anchor


def test_bbox_overlay_style() -> None:
    style = bbox_overlay_style((0.1, 0.2, 0.5, 0.4))
    assert "left:10.0000%" in style
    assert "width:40.0000%" in style
    assert "height:20.0000%" in style


def test_highlight_html_includes_overlay() -> None:
    claim = Claim(
        identity_key=identity_key("BYMA", "2026-03-31", SCOPE_CONSOLIDADO, METRIC_NETO),
        value="21262335",
        period="2026-03-31",
        source_page=4,
        source_text="RESULTADO NETO DEL PERÍODO",
        issuer="BYMA",
        scope=SCOPE_CONSOLIDADO,
        metric=METRIC_NETO,
        source_bbox=(0.1, 0.2, 0.5, 0.4),
    )
    html = highlight_html(claim, image_rel="assets/page.png", pdf_name="eeff.pdf")
    assert highlight_anchor(claim.identity_key) in html
    assert "bbox-overlay" in html
    assert "assets/page.png" in html


def test_write_review_pack_creates_html(tmp_path: Path) -> None:
    claim = Claim(
        identity_key=identity_key("BYMA", "2026-03-31", SCOPE_CONSOLIDADO, METRIC_NETO),
        value="21262335",
        period="2026-03-31",
        source_page=4,
        source_text="RESULTADO NETO DEL PERÍODO",
        issuer="BYMA",
        scope=SCOPE_CONSOLIDADO,
        metric=METRIC_NETO,
        source_bbox=(0.1, 0.2, 0.5, 0.4),
    )
    out = tmp_path / "review" / "index.html"
    write_review_pack(out, (claim,))
    text = out.read_text(encoding="utf-8")
    assert "hitl-highlights" in text
    assert "bbox-overlay" in text
