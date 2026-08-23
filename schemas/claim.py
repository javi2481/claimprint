"""Typed claim: domain-agnostic identity + value + provenance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Route = Literal["identity", "abstain", "narrative"]

SCOPE_CONSOLIDADO = "consolidado"
SCOPE_CONTROLANTE = "controlante"
METRIC_NETO = "resultado_neto"
METRIC_ATRIBUIBLE = "resultado_atribuible_controladora"
METRIC_BRUTO = "resultado_bruto"
METRIC_OPERATIVO = "resultado_operativo"
METRIC_EBT = "resultado_antes_impuesto"
METRIC_IMPUESTO = "impuesto_ganancias"
METRIC_NCI = "resultado_no_controlante"
SCOPE_PRESS = "comunicado"
METRIC_PRESS_AS_OF = "press_as_of_date"
METRIC_PRESS_PERIOD = "press_period"
METRIC_PRESS_EBITDA_MARGIN_LTM = "press_ebitda_margin_ltm"
SCOPE_PRESENTATION = "presentacion"
METRIC_PRESENTATION_EBITDA = "presentation_ebitda"
METRIC_PRESENTATION_EBITDA_MARGIN_LTM = "presentation_ebitda_margin_ltm"


class ClaimError(ValueError):
    """Claim failed integrity checks."""


def validate_claim(claim: "Claim") -> None:
    if not (claim.value or "").strip():
        raise ClaimError("empty value")
    if not (claim.period or "").strip():
        raise ClaimError("empty period")
    if claim.source_page is not None and claim.source_page <= 0:
        raise ClaimError("source_page must be > 0 when set")
    if claim.issuer and claim.scope and claim.metric:
        expected = identity_key(claim.issuer, claim.period, claim.scope, claim.metric)
        if claim.identity_key != expected:
            raise ClaimError("identity_key inconsistent with issuer|period|scope|metric")


def identity_key(issuer: str, period: str, scope: str, metric: str) -> str:
    return f"{issuer}|{period}|{scope}|{metric}"


@dataclass(frozen=True)
class Claim:
    identity_key: str
    value: str
    period: str
    source_page: int | None
    source_text: str | None
    issuer: str | None = None
    scope: str | None = None
    metric: str | None = None
    document_id: str | None = None
    source_bbox: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        if self.source_page is not None and self.source_page <= 0:
            raise ClaimError("source_page must be > 0 when set")
        if (
            (self.value or "").strip()
            and (self.period or "").strip()
            and self.issuer
            and self.scope
            and self.metric
        ):
            expected = identity_key(self.issuer, self.period, self.scope, self.metric)
            if self.identity_key != expected:
                raise ClaimError("identity_key inconsistent with issuer|period|scope|metric")


def claims_from_financial_statement(row: object) -> tuple[Claim, ...]:
    """Project the BYMA financial-statement DTO into consolidado and controlante claims.

    Press and presentation have their own projectors. This repository ships
    one domain (finance); there is no second-domain registry.
    """
    from schemas.financial_statement import FinancialStatement

    if not isinstance(row, FinancialStatement):
        raise TypeError("finance projector expects FinancialStatement")
    issuer = (row.issuer or "").strip()
    if not issuer:
        return ()
    period = row.period
    page = row.source_page
    consolidado = Claim(
        identity_key=identity_key(issuer, period, SCOPE_CONSOLIDADO, METRIC_NETO),
        value=row.net_income_consolidated or "",
        period=period,
        source_page=page,
        source_text=row.source_text_consolidado,
        issuer=issuer,
        scope=SCOPE_CONSOLIDADO,
        metric=METRIC_NETO,
    )
    controlante = Claim(
        identity_key=identity_key(issuer, period, SCOPE_CONTROLANTE, METRIC_ATRIBUIBLE),
        value=row.net_income_attributable_to_parent or "",
        period=period,
        source_page=page,
        source_text=row.source_text_controlante,
        issuer=issuer,
        scope=SCOPE_CONTROLANTE,
        metric=METRIC_ATRIBUIBLE,
    )
    return (consolidado, controlante)
