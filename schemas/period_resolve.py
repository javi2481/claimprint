"""Content-first quarter period resolution for press and presentation."""

from __future__ import annotations

import re

from schemas.parse_artifact import fold

PERIOD_1T26 = "2026-03-31"
PERIOD_2T26 = "2026-06-30"
LABEL_1T26 = "1T26"
LABEL_2T26 = "2T26"

_QUARTER_1 = re.compile(
    r"1\s*[°ºo]?\s*trimestre\s+2026|\(1t26\)|\b1t26\b",
    re.IGNORECASE,
)
_QUARTER_2 = re.compile(
    r"2\s*[°ºo]?\s*trimestre\s+2026|\(2t26\)|\b2t26\b",
    re.IGNORECASE,
)
_PERIOD_END_MAR_2026 = re.compile(
    r"31\s+de\s+marzo\s+de\s+2026",
    re.IGNORECASE,
)
_PERIOD_END_JUN_2026 = re.compile(
    r"30\s+de\s+junio\s+de\s+2026",
    re.IGNORECASE,
)


def _quarter_from_blob(blob: str) -> tuple[str, str] | None:
    folded = fold(blob)
    has_1 = bool(_QUARTER_1.search(folded))
    has_2 = bool(_QUARTER_2.search(folded))
    if has_1 and not has_2:
        return PERIOD_1T26, LABEL_1T26
    if has_2 and not has_1:
        return PERIOD_2T26, LABEL_2T26
    if _PERIOD_END_MAR_2026.search(folded) and not has_2:
        return PERIOD_1T26, LABEL_1T26
    if _PERIOD_END_JUN_2026.search(folded) and not has_1:
        return PERIOD_2T26, LABEL_2T26
    return None


def resolve_quarter_period(
    *,
    front_matter: str,
    filename: str,
    body: str = "",
) -> tuple[str, str] | None:
    """Return (iso_period, label). Content-first, filename fallback."""
    for blob in (front_matter, body):
        if not blob.strip():
            continue
        row = _quarter_from_blob(blob)
        if row is not None:
            return row
    name = fold(filename)
    if "1t26" in name:
        return PERIOD_1T26, LABEL_1T26
    if "2t26" in name:
        return PERIOD_2T26, LABEL_2T26
    return None
