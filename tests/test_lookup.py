"""Layer 2: lexical identity lookup. No RAGFlow."""

from __future__ import annotations

import pytest

from schemas.claim import SCOPE_CONSOLIDADO, SCOPE_CONTROLANTE
from schemas.corpus import extract_claims_from_dir
from schemas.lookup import lookup, understand
from schemas.parse_artifact import fixtures_ready

needs_parse = pytest.mark.skipif(
    not fixtures_ready(),
    reason="missing MinerU fixtures (run scripts/export_mineru.py)",
)


@pytest.fixture(scope="module")
def claims():
    if not fixtures_ready():
        pytest.skip("missing MinerU fixtures (run scripts/export_mineru.py)")
    return extract_claims_from_dir()


def test_default_consolidado_trap(claims) -> None:
    result = lookup("¿Cuál es el resultado neto del período 1T26?", claims)
    assert result.route == "identity"
    assert len(result.claims) == 1
    row = result.claims[0]
    assert row.scope == SCOPE_CONSOLIDADO
    assert row.value == "21262335"
    assert row.value != "21259769"
    assert row.value != "22362983"
    assert row.source_page == 4
    assert row.source_text


def test_ganancia_neta_routes_to_consolidado(claims) -> None:
    result = lookup("¿Cuál es la ganancia neta del 1T26?", claims)
    assert result.route == "identity"
    assert result.claims[0].scope == SCOPE_CONSOLIDADO
    assert result.claims[0].value == "21262335"


def test_utilidad_neta_routes_to_consolidado(claims) -> None:
    result = lookup("¿Cuál es la utilidad neta del 1T26?", claims)
    assert result.route == "identity"
    assert result.claims[0].scope == SCOPE_CONSOLIDADO
    assert result.claims[0].value == "21262335"


def test_ganancia_neta_on_comunicado_abstains(claims) -> None:
    result = lookup("¿Cuál es la ganancia neta consolidada del comunicado de prensa?", claims)
    assert result.route == "abstain"
    assert result.claims == ()


def test_understand_ganancia_neta_not_narrative() -> None:
    intent = understand("Explicá la ganancia neta del 1T26")
    assert intent.route == "identity"
    assert intent.scope == SCOPE_CONSOLIDADO
    assert intent.metric == "resultado_neto"


def test_explicit_controlante(claims) -> None:
    result = lookup("Resultado atribuible a la participación controlante 1T26", claims)
    assert result.route == "identity"
    assert result.claims[0].scope == SCOPE_CONTROLANTE
    assert result.claims[0].value == "21259769"


def test_no_controlante_is_not_neto(claims) -> None:
    result = lookup("Resultado atribuible a la participación no controlante 1T26", claims)
    assert result.route == "identity"
    row = result.claims[0]
    assert row.metric == "resultado_no_controlante"
    assert row.value == "2566"
    assert row.value != "21262335"
    assert row.value != "21259769"


def test_bruto_not_operativo(claims) -> None:
    result = lookup("¿Cuál es el resultado bruto del 1T26?", claims)
    assert result.route == "identity"
    assert result.claims[0].value == "60144176"
    assert result.claims[0].value != "70223471"
    assert result.claims[0].value != "21262335"


def test_compare_same_identity(claims) -> None:
    result = lookup("Comparar resultado neto consolidado 1T26 vs 2T26", claims)
    assert result.route == "identity"
    assert result.compare is True
    scopes = {c.scope for c in result.claims}
    assert scopes == {SCOPE_CONSOLIDADO}
    values = {c.value for c in result.claims}
    assert values == {"21262335", "81956525"}
    assert "21259769" not in values
    assert "81946993" not in values


def test_ypf_abstains(claims) -> None:
    result = lookup("¿Cuál fue el precio de cierre de YPF en BYMA el 3 de enero?", claims)
    assert result.route == "abstain"
    assert result.claims == ()


def test_press_date_not_pnl(claims) -> None:
    result = lookup("¿Cuál es la fecha del comunicado de prensa 1T26?", claims)
    assert result.route == "identity"
    row = result.claims[0]
    assert row.metric == "press_as_of_date"
    assert row.value == "2026-05-08"
    assert row.value != "21262335"


def test_presentation_ebitda_not_pnl(claims) -> None:
    result = lookup("¿Cuál es el EBITDA de la presentación 1T26?", claims)
    assert result.route == "identity"
    row = result.claims[0]
    assert row.metric == "presentation_ebitda"
    assert row.value == "72128"
    assert row.value != "21262335"


def test_eeff_metric_on_presentation_abstains(claims) -> None:
    result = lookup("¿Cuál es el resultado neto consolidado de la presentación de resultados?", claims)
    assert result.route == "abstain"
    assert result.claims == ()


def test_neto_de_la_memoria_abstains(claims) -> None:
    result = lookup("¿Cuál es el resultado neto de la memoria?", claims)
    assert result.route == "abstain"
    assert result.claims == ()


def test_eeff_metric_on_comunicado_still_abstains(claims) -> None:
    result = lookup("¿Cuál es el resultado neto consolidado del comunicado de prensa?", claims)
    assert result.route == "abstain"
    assert result.claims == ()


def test_lote2_identity_values(claims) -> None:
    """Manual chat lote-2 gold (distinct from rag_chat_v1)."""
    cases = [
        ("¿Cuál es el resultado bruto del 1T26?", "60144176"),
        ("¿Cuál es el resultado operativo del 1T26?", "70223471"),
        ("¿Cuál es el impuesto a las ganancias del 1T26?", "-14950948"),
        ("Resultado atribuible a la participación no controlante 1T26", "2566"),
        ("Resultado bruto 2T26", "122610546"),
        ("¿Cuál es la fecha del comunicado de prensa 2T26?", "2026-08-07"),
        ("margen EBITDA de los últimos 12 meses del comunicado 2T26", "75"),
        ("¿Cuál es el EBITDA de la presentación 2T26?", "71697"),
    ]
    for question, expected in cases:
        result = lookup(question, claims)
        assert result.route == "identity", question
        assert result.claims[0].value == expected, question


def test_press_ltm_not_presentation_and_not_neto(claims) -> None:
    result = lookup("¿Cuál es el margen EBITDA LTM del comunicado de prensa 1T26?", claims)
    assert result.route == "identity"
    row = result.claims[0]
    assert row.metric == "press_ebitda_margin_ltm"
    assert row.scope == "comunicado"
    assert row.value == "76"
    assert row.source_page == 2
    assert row.value != "72128"
    assert row.value != "21262335"


def test_bare_ebitda_on_comunicado_abstains(claims) -> None:
    result = lookup("¿Cuál es el EBITDA del comunicado de prensa 1T26?", claims)
    assert result.route == "abstain"
    assert result.claims == ()


def test_understand_narrative_is_not_identity() -> None:
    intent = understand("Explicá el crecimiento de ingresos de BYMA")
    assert intent.route == "narrative"


def test_no_ragflow_import() -> None:
    import inspect

    import schemas.extract as extract_mod
    import schemas.lookup as lookup_mod

    for module in (lookup_mod, extract_mod):
        source = inspect.getsource(module)
        assert "ragflow" not in source.lower()
        assert "voyage" not in source.lower()
        assert "infinity" not in source.lower()
