"""PDF page thumbnails with normalized bbox overlay for HITL review."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from schemas.claim import Claim
from schemas.corpus import SAMPLES

Bbox = tuple[float, float, float, float]
_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def pdftoppm_available() -> bool:
    return shutil.which("pdftoppm") is not None


def _safe_stem(name: str) -> str:
    return _SAFE.sub("_", Path(name).stem)[:80]


def page_png_path(assets_dir: Path, pdf_name: str, page: int) -> Path:
    return assets_dir / f"{_safe_stem(pdf_name)}_p{page}.png"


def render_pdf_page(pdf: Path, page: int, dest: Path) -> bool:
    """Render one PDF page to PNG via poppler pdftoppm. Returns False if unavailable."""
    if page < 1 or not pdf.is_file() or not pdftoppm_available():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    prefix = dest.with_suffix("")
    proc = subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-f",
            str(page),
            "-l",
            str(page),
            "-singlefile",
            str(pdf),
            str(prefix),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    produced = Path(f"{prefix}.png")
    if proc.returncode != 0 or not produced.is_file():
        return False
    if produced != dest:
        produced.replace(dest)
    return dest.is_file()


def bbox_overlay_style(bbox: Bbox) -> str:
    x0, y0, x1, y1 = bbox
    return (
        f"left:{x0 * 100:.4f}%;top:{y0 * 100:.4f}%;"
        f"width:{max(0.0, x1 - x0) * 100:.4f}%;height:{max(0.0, y1 - y0) * 100:.4f}%;"
    )


def highlight_anchor(identity_key: str) -> str:
    return f"hl-{_safe_stem(identity_key)}"


def highlight_html(
    claim: Claim,
    *,
    image_rel: str | None,
    pdf_name: str,
) -> str:
    if claim.source_bbox is None or claim.source_page is None:
        return ""
    overlay = bbox_overlay_style(claim.source_bbox)
    bg = (
        f"background-image:url('{image_rel}');background-size:contain;background-repeat:no-repeat;"
        if image_rel
        else "background:#f4f4f4;"
    )
    caption = f"{pdf_name} · p.{claim.source_page}"
    return (
        f'<figure class="hitl-highlight" id="{highlight_anchor(claim.identity_key)}">'
        f'<figcaption>{caption}</figcaption>'
        f'<div class="page-frame"><div class="page-surface" style="{bg}">'
        f'<div class="bbox-overlay" style="{overlay}"></div>'
        f"</div></div></figure>"
    )


def ensure_page_asset(
    pdf: Path,
    page: int,
    assets_dir: Path,
) -> str | None:
    dest = page_png_path(assets_dir, pdf.name, page)
    if dest.is_file():
        return f"assets/{dest.name}"
    if render_pdf_page(pdf, page, dest):
        return f"assets/{dest.name}"
    return None


def pdf_for_claim(claim: Claim, samples: Path | None = None) -> Path | None:
    folder = samples or SAMPLES
    if not claim.document_id:
        return None
    for pdf in sorted(folder.glob("*.pdf")):
        from schemas.provenance import pdf_document_id

        if pdf_document_id(pdf) == claim.document_id:
            return pdf
    return None


HIGHLIGHT_CSS = """
.hitl-highlights{margin-top:32px}
.hitl-highlight{margin:16px 0 24px}
.hitl-highlight figcaption{font-size:13px;color:#444;margin-bottom:6px}
.page-frame{max-width:720px;border:1px solid #ccc;background:#fff;padding:4px}
.page-surface{position:relative;width:100%;aspect-ratio:8.5/11;min-height:200px}
.bbox-overlay{position:absolute;border:2px solid #dc2626;background:rgba(220,38,38,0.18);box-sizing:border-box}
"""
