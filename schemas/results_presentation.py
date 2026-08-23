"""Results presentation: EBITDA + LTM margin from highlights. Not P&L."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

from schemas.catalog import Recipe, load_recipes
from schemas.claim import (
    METRIC_PRESENTATION_EBITDA,
    METRIC_PRESENTATION_EBITDA_MARGIN_LTM,
    SCOPE_PRESENTATION,
    Claim,
    identity_key,
)
from schemas.classify import UNKNOWN, classify_artifact
from schemas.extract import _issuer_from_text, select_page
from schemas.money import digits_ars
from schemas.parse_artifact import load_parse, page_text
from schemas.period_resolve import resolve_quarter_period


class ResultsPresentation(BaseModel):
    issuer: str | None = Field(default=None)
    period: str
    ebitda: str
    ebitda_margin_ltm: str
    source_page: int | None = None
    source_text_ebitda: str | None = None
    source_text_margin: str | None = None


def _period_from_text_and_name(
    text: str,
    filename: str,
    *,
    front_matter: str = "",
) -> str | None:
    row = resolve_quarter_period(front_matter=front_matter, filename=filename, body=text)
    return row[0] if row else None


def fill_results_presentation(
    text: str,
    *,
    source_page: int,
    filename: str,
    front_matter: str = "",
) -> ResultsPresentation | None:
    period = _period_from_text_and_name(text, filename, front_matter=front_matter)
    if period is None:
        return None
    raw_ebitda = re.search(
        r"Alcanzamos un EBITDA de ARS\s+([\d.,]+)\s*millones",
        text,
        re.IGNORECASE,
    )
    raw_margin = re.search(
        r"margen EBITDA de los [uú]ltimos 12 meses[^\d]{0,80}(\d{2})\s*%",
        text,
        re.IGNORECASE,
    )
    if raw_ebitda is None or raw_margin is None:
        return None
    digits = digits_ars(raw_ebitda.group(1))
    if not digits:
        digits = "".join(ch for ch in raw_ebitda.group(1) if ch.isdigit())
    if not digits:
        return None
    issuer = _issuer_from_text(text, filename)
    if not issuer:
        return None
    return ResultsPresentation(
        issuer=issuer,
        period=period,
        ebitda=digits,
        ebitda_margin_ltm=raw_margin.group(1),
        source_page=source_page,
        source_text_ebitda=raw_ebitda.group(0),
        source_text_margin=raw_margin.group(0),
    )


def claims_from_results_presentation(row: ResultsPresentation) -> tuple[Claim, ...]:
    issuer = (row.issuer or "").strip()
    if not issuer:
        return ()
    page = row.source_page
    ebitda = Claim(
        identity_key=identity_key(issuer, row.period, SCOPE_PRESENTATION, METRIC_PRESENTATION_EBITDA),
        value=row.ebitda,
        period=row.period,
        source_page=page,
        source_text=row.source_text_ebitda,
        issuer=issuer,
        scope=SCOPE_PRESENTATION,
        metric=METRIC_PRESENTATION_EBITDA,
    )
    margin = Claim(
        identity_key=identity_key(
            issuer, row.period, SCOPE_PRESENTATION, METRIC_PRESENTATION_EBITDA_MARGIN_LTM
        ),
        value=row.ebitda_margin_ltm,
        period=row.period,
        source_page=page,
        source_text=row.source_text_margin,
        issuer=issuer,
        scope=SCOPE_PRESENTATION,
        metric=METRIC_PRESENTATION_EBITDA_MARGIN_LTM,
    )
    return (ebitda, margin)


def extract_results_presentation(
    pdf: Path, recipes: dict[str, Recipe] | None = None
) -> ResultsPresentation | None:
    catalog = recipes if recipes is not None else load_recipes()
    artifact = load_parse(pdf)
    if artifact is None:
        return None
    recipe_id = classify_artifact(artifact, tuple(catalog))
    if recipe_id == UNKNOWN:
        return None
    recipe = catalog.get(recipe_id)
    if recipe is None or not recipe.extract or recipe.id != "results_presentation":
        return None
    page = select_page(pdf, recipe.page_select_keywords, artifact=artifact)
    if page is None:
        return None
    text = page_text(artifact, page)
    return fill_results_presentation(
        text,
        source_page=page,
        filename=pdf.name,
        front_matter=artifact.front_matter,
    )
