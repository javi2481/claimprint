"""Claim integrity for v1 close."""

import pytest

from schemas.claim import Claim, ClaimError, identity_key, validate_claim


def test_validate_claim_rejects_bad_page() -> None:
    with pytest.raises(ClaimError):
        Claim(
            identity_key=identity_key("BYMA", "2026-03-31", "consolidado", "resultado_neto"),
            value="1",
            period="2026-03-31",
            source_page=-1,
            source_text="x",
            issuer="BYMA",
            scope="consolidado",
            metric="resultado_neto",
        )


def test_constructor_rejects_empty_value() -> None:
    with pytest.raises(ClaimError, match="empty value"):
        Claim(
            identity_key="x",
            value="",
            period="2026-03-31",
            source_page=None,
            source_text=None,
        )


def test_constructor_rejects_empty_period() -> None:
    with pytest.raises(ClaimError, match="empty period"):
        Claim(
            identity_key="x",
            value="1",
            period="",
            source_page=None,
            source_text=None,
        )


def test_constructor_rejects_invalid_bbox() -> None:
    with pytest.raises(ClaimError, match="source_bbox"):
        Claim(
            identity_key=identity_key("BYMA", "2026-03-31", "consolidado", "resultado_neto"),
            value="1",
            period="2026-03-31",
            source_page=4,
            source_text="x",
            issuer="BYMA",
            scope="consolidado",
            metric="resultado_neto",
            source_bbox=(0.5, 0.2, 0.1, 0.8),
        )


def test_validate_claim_ok() -> None:
    c = Claim(
        identity_key=identity_key("BYMA", "2026-03-31", "consolidado", "resultado_neto"),
        value="1",
        period="2026-03-31",
        source_page=4,
        source_text="x",
        issuer="BYMA",
        scope="consolidado",
        metric="resultado_neto",
        source_bbox=(0.1, 0.2, 0.5, 0.4),
    )
    validate_claim(c)
