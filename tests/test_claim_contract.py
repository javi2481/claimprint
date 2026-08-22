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
    )
    validate_claim(c)
