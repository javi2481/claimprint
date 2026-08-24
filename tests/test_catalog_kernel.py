"""Catalog kernel: recipes are plugins; financial_statement is not required."""

from __future__ import annotations

import json
from pathlib import Path

from schemas.catalog import classifier_labels, load_recipes
from schemas.claim import claims_from_financial_statement, identity_key
from schemas.financial_statement import FinancialStatement
from schemas.validate import reject_financial_statement


def test_catalog_without_financial_statement(tmp_path: Path) -> None:
    payload = {
        "id": "press_release",
        "extract": False,
        "description": "solo una receta",
        "threshold": 0.85,
        "page_select_keywords": [],
        "gold": {},
    }
    (tmp_path / "press_release.json").write_text(json.dumps(payload), encoding="utf-8")
    recipes = load_recipes(tmp_path)
    assert "financial_statement" not in recipes
    assert set(recipes) == {"press_release"}
    labels = classifier_labels(recipes)
    assert labels[-1] == "UNKNOWN"
    assert "press_release" in labels


def test_empty_catalog_still_fails(tmp_path: Path) -> None:
    try:
        load_recipes(tmp_path)
    except ValueError as exc:
        assert "catalog empty" in str(exc)
    else:
        raise AssertionError("expected catalog empty")


def test_claims_from_valid_statement() -> None:
    gold = load_recipes()["financial_statement"].gold["BYMA_-_EEFF_31-03-2026_VF.pdf"]
    row = FinancialStatement(
        issuer="BYMA",
        period=gold["period"],
        net_income_consolidated=gold["net_income_consolidated"],
        net_income_attributable_to_parent=gold["net_income_attributable_to_parent"],
        source_page=4,
        source_text_consolidado="RESULTADO NETO DEL PERÍODO",
        source_text_controlante="participación controlante",
    )
    assert reject_financial_statement(row) is None
    claims = claims_from_financial_statement(row)
    keys = {c.identity_key for c in claims}
    assert identity_key("BYMA", "2026-03-31", "consolidado", "resultado_neto") in keys
    assert identity_key("BYMA", "2026-03-31", "controlante", "resultado_atribuible_controladora") in keys
    values = {c.identity_key: c.value for c in claims}
    cons = identity_key("BYMA", "2026-03-31", "consolidado", "resultado_neto")
    ctrl = identity_key("BYMA", "2026-03-31", "controlante", "resultado_atribuible_controladora")
    assert values[cons] != values[ctrl]


def test_claims_partial_consolidado_only() -> None:
    row = FinancialStatement(
        issuer="BYMA",
        period="2026-03-31",
        net_income_consolidated="21262335",
        source_page=4,
        source_text_consolidado="RESULTADO NETO DEL PERÍODO",
    )
    claims = claims_from_financial_statement(row)
    assert len(claims) == 1
    assert claims[0].scope == "consolidado"
    assert claims[0].metric == "resultado_neto"
    assert claims[0].value == "21262335"


def test_claims_partial_controlante_only() -> None:
    row = FinancialStatement(
        issuer="BYMA",
        period="2026-03-31",
        net_income_attributable_to_parent="21259769",
        source_page=4,
        source_text_controlante="participación controlante",
    )
    claims = claims_from_financial_statement(row)
    assert len(claims) == 1
    assert claims[0].scope == "controlante"
    assert claims[0].metric == "resultado_atribuible_controladora"
    assert claims[0].value == "21259769"


def test_claims_both_empty_returns_empty() -> None:
    row = FinancialStatement(issuer="BYMA", period="2026-03-31")
    assert claims_from_financial_statement(row) == ()


def test_reject_before_claims() -> None:
    row = FinancialStatement(
        period="2026-03-31",
        net_income_consolidated="21262335",
        net_income_attributable_to_parent="21262335",
    )
    assert reject_financial_statement(row) == "consolidado equals controlante"
