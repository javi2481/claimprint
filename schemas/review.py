"""HITL verdicts over typed claims. Missing file = accept-all."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from schemas.claim import Claim
from schemas.review_highlight import HIGHLIGHT_CSS, ensure_page_asset, highlight_anchor, highlight_html, pdf_for_claim

Verdict = Literal["accept", "reject", "flag"]
VALID = frozenset({"accept", "reject", "flag"})


def load_verdicts(path: Path | None) -> dict[str, Verdict]:
    """Return identity_key -> verdict. Missing/corrupt file yields empty (accept-all)."""
    if path is None or not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = raw.get("verdicts") if isinstance(raw, dict) else raw
    if not isinstance(rows, dict):
        return {}
    out: dict[str, Verdict] = {}
    for key, value in rows.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        if value in VALID:
            out[key] = value  # type: ignore[assignment]
    return out


def verdict_for(identity_key: str, verdicts: dict[str, Verdict]) -> Verdict:
    return verdicts.get(identity_key, "accept")


def publishable(
    claims: tuple[Claim, ...] | list[Claim],
    verdicts: dict[str, Verdict] | None = None,
) -> tuple[Claim, ...]:
    table = verdicts or {}
    return tuple(c for c in claims if verdict_for(c.identity_key, table) == "accept")


def flagged(
    claims: tuple[Claim, ...] | list[Claim],
    verdicts: dict[str, Verdict] | None = None,
) -> tuple[Claim, ...]:
    table = verdicts or {}
    return tuple(c for c in claims if verdict_for(c.identity_key, table) == "flag")


def rejected(
    claims: tuple[Claim, ...] | list[Claim],
    verdicts: dict[str, Verdict] | None = None,
) -> tuple[Claim, ...]:
    table = verdicts or {}
    return tuple(c for c in claims if verdict_for(c.identity_key, table) == "reject")


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _format_bbox(bbox: tuple[float, float, float, float] | None) -> str:
    if bbox is None:
        return ""
    return ",".join(f"{v:.4f}" for v in bbox)


def render_review_html(
    claims: tuple[Claim, ...] | list[Claim],
    *,
    verdicts: dict[str, Verdict] | None = None,
    highlight_section: str = "",
) -> str:
    table = verdicts or {}
    rows: list[str] = []
    for claim in claims:
        mark = verdict_for(claim.identity_key, table)
        page = "" if claim.source_page is None else str(claim.source_page)
        snippet = claim.source_text or ""
        doc_id = claim.document_id or ""
        if len(doc_id) > 12:
            doc_id = doc_id[:12] + "…"
        src_hash = claim.parse_artifact_hash or ""
        if len(src_hash) > 12:
            src_hash = src_hash[:12] + "…"
        bbox = _format_bbox(claim.source_bbox)
        hl = ""
        if claim.source_bbox is not None:
            hl = f'<a href="#{highlight_anchor(claim.identity_key)}">ver</a>'
        rows.append(
            "<tr>"
            f"<td>{_esc(claim.identity_key)}</td>"
            f"<td>{_esc(claim.value)}</td>"
            f"<td>{_esc(page)}</td>"
            f"<td>{_esc(snippet)}</td>"
            f"<td>{_esc(doc_id)}</td>"
            f"<td>{_esc(src_hash)}</td>"
            f"<td>{_esc(bbox)}</td>"
            f"<td>{hl}</td>"
            f"<td>{_esc(mark)}</td>"
            "</tr>"
        )
    body = "\n".join(rows) if rows else "<tr><td colspan='9'>Sin claims</td></tr>"
    highlights = (
        f'<section class="hitl-highlights"><h2>Evidencia visual (bbox)</h2>{highlight_section}</section>'
        if highlight_section
        else ""
    )
    return (
        "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
        "<title>Revisión HITL Claimprint</title>"
        f"<style>body{{font-family:sans-serif;margin:24px}}table{{border-collapse:collapse;width:100%}}"
        "th,td{border:1px solid #ccc;padding:6px;text-align:left;font-size:14px}"
        f"th{{background:#f4f4f4}}{HIGHLIGHT_CSS}</style></head><body>"
        "<h1>Revisión humana (HITL asistido)</h1>"
        "<p>Marcá accept / reject / flag en el JSON de veredictos. "
        "Sin archivo, todo cuenta como accept. "
        "Rectángulo rojo = <code>source_bbox</code> normalizado sobre la página del PDF.</p>"
        "<table><thead><tr><th>identity_key</th><th>valor</th><th>página</th>"
        "<th>source_text</th><th>document_id</th><th>parse_artifact_hash</th><th>source_bbox</th>"
        "<th></th><th>veredicto</th></tr></thead><tbody>"
        f"{body}</tbody></table>{highlights}</body></html>"
    )


def write_review_pack(
    out_html: Path,
    claims: tuple[Claim, ...] | list[Claim],
    *,
    verdicts: dict[str, Verdict] | None = None,
    samples: Path | None = None,
) -> Path:
    """Write index.html plus optional page PNGs under assets/."""
    assets_dir = out_html.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    figures: list[str] = []
    rendered_pages: dict[tuple[str, int], str | None] = {}
    for claim in claims:
        if claim.source_bbox is None or claim.source_page is None:
            continue
        pdf = pdf_for_claim(claim, samples)
        if pdf is None:
            figures.append(
                highlight_html(claim, image_rel=None, pdf_name="(pdf no resuelto)")
            )
            continue
        key = (pdf.name, claim.source_page)
        if key not in rendered_pages:
            rendered_pages[key] = ensure_page_asset(pdf, claim.source_page, assets_dir)
        figures.append(
            highlight_html(
                claim,
                image_rel=rendered_pages[key],
                pdf_name=pdf.name,
            )
        )
    html = render_review_html(
        claims,
        verdicts=verdicts,
        highlight_section="\n".join(figures),
    )
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")
    return out_html
