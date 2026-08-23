"""PDF document_id and bbox match from MinerU content sidecars."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path

from schemas.claim import Claim
from schemas.extract import fold
from schemas.mineru_artifact import ContentSidecar, load_content_sidecar
from schemas.parse_artifact import parse_sha256
from schemas.money import digits_ars, format_display_ars

Bbox = tuple[float, float, float, float]


def pdf_document_id(pdf: Path) -> str:
    digest = hashlib.sha256()
    with pdf.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digits_only(text: str) -> str:
    return "".join(ch for ch in text if ch.isdigit())


def _value_needles(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    raw = (value or "").strip()
    if not raw:
        return ()
    needles: list[str] = []
    digits = digits_ars(raw) or _digits_only(raw)
    if digits:
        needles.append(digits)
    try:
        display = format_display_ars(raw)
        if display and display not in needles:
            needles.append(display)
    except (ValueError, TypeError):
        pass
    if raw not in needles:
        needles.append(raw)
    return tuple(needles)


def _span_candidates(
    sidecar: ContentSidecar,
    *,
    page: int | None,
) -> tuple:
    spans = sidecar.spans
    if page is not None and page > 0:
        spans = tuple(span for span in spans if span.page == page)
    return tuple(span for span in spans if span.bbox_norm is not None)


def _score_span(
    span_text: str,
    *,
    source_text: str | None,
    value_needles: tuple[str, ...],
) -> int:
    folded = fold(span_text)
    score = 0
    label = fold(source_text or "")
    if label and len(label) >= 8 and label in folded:
        score += 2
    elif label and len(label) >= 4:
        tokens = [token for token in re.split(r"\s+", label) if len(token) >= 4]
        if tokens and all(token in folded for token in tokens[:3]):
            score += 1
    if value_needles:
        span_digits = _digits_only(span_text)
        for needle in value_needles:
            if needle.isdigit():
                if needle in span_digits:
                    score += 1
                    break
            elif needle.casefold() in span_text.casefold():
                score += 1
                break
    return score


def match_bbox(
    sidecar: ContentSidecar | Path,
    *,
    source_text: str | None,
    page: int | None,
    value: str | None = None,
) -> Bbox | None:
    """Return normalized bbox when a sidecar span contains source_text or value."""
    loaded: ContentSidecar | None
    if isinstance(sidecar, Path):
        raw = json.loads(sidecar.read_text(encoding="utf-8"))
        loaded = ContentSidecar.from_dict(raw) if isinstance(raw, dict) else None
    else:
        loaded = sidecar
    if loaded is None:
        return None

    value_needles = _value_needles(value)
    if not (source_text or value_needles):
        return None

    best_score = 0
    best_bbox: Bbox | None = None
    best_len = 10**9
    for span in _span_candidates(loaded, page=page):
        score = _score_span(span.text, source_text=source_text, value_needles=value_needles)
        if score <= 0:
            continue
        span_len = len(span.text)
        if score > best_score or (score == best_score and span_len < best_len):
            best_score = score
            best_bbox = span.bbox_norm
            best_len = span_len
    return best_bbox


def enrich_claim_provenance(
    claim: Claim,
    pdf: Path,
    fixtures: Path | None = None,
) -> Claim:
    doc_id = pdf_document_id(pdf)
    src_hash = parse_sha256(pdf, fixtures)
    sidecar = load_content_sidecar(pdf, fixtures)
    bbox = (
        match_bbox(
            sidecar,
            source_text=claim.source_text,
            page=claim.source_page,
            value=claim.value,
        )
        if sidecar is not None
        else None
    )
    return replace(
        claim,
        document_id=doc_id,
        source_hash=src_hash,
        source_bbox=bbox,
    )
