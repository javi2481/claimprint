"""HITL verdicts over typed claims. Missing file = accept-all."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from schemas.claim import Claim

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
        bbox = _format_bbox(claim.source_bbox)
        rows.append(
            "<tr>"
            f"<td>{_esc(claim.identity_key)}</td>"
            f"<td>{_esc(claim.value)}</td>"
            f"<td>{_esc(page)}</td>"
            f"<td>{_esc(snippet)}</td>"
            f"<td>{_esc(doc_id)}</td>"
            f"<td>{_esc(bbox)}</td>"
            f"<td>{_esc(mark)}</td>"
            "</tr>"
        )
    body = "\n".join(rows) if rows else "<tr><td colspan='7'>Sin claims</td></tr>"
    return (
        "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
        "<title>Revisión HITL Claimprint</title>"
        "<style>body{font-family:sans-serif;margin:24px}table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #ccc;padding:6px;text-align:left;font-size:14px}"
        "th{background:#f4f4f4}</style></head><body>"
        "<h1>Revisión humana (HITL asistido)</h1>"
        "<p>Marcá accept / reject / flag en el JSON de veredictos. "
        "Sin archivo, todo cuenta como accept.</p>"
        "<table><thead><tr><th>identity_key</th><th>valor</th><th>página</th>"
        "<th>source_text</th><th>document_id</th><th>source_bbox</th><th>veredicto</th></tr></thead><tbody>"
        f"{body}</tbody></table></body></html>"
    )
