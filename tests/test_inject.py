"""Kernel claims → RAGFlow ficha text. No HTTP."""

from __future__ import annotations

from schemas.claim import (
    METRIC_ATRIBUIBLE,
    METRIC_BRUTO,
    METRIC_IMPUESTO,
    METRIC_NCI,
    METRIC_NETO,
    METRIC_OPERATIVO,
    SCOPE_CONSOLIDADO,
    SCOPE_CONTROLANTE,
    Claim,
    identity_key,
)
from schemas.inject import (
    IDP_START,
    MARKER,
    MARKER_GRAPH,
    eeff_chunk,
    is_inject_chunk,
    prompt_lines,
    strip_idp_prompt,
    upsert_idp_prompt,
)
from schemas.money import format_display_ars


def _claim(period: str, scope: str, metric: str, value: str, page: int = 4) -> Claim:
    return Claim(
        identity_key=identity_key("BYMA", period, scope, metric),
        value=value,
        period=period,
        source_page=page,
        source_text=metric,
        issuer="BYMA",
        scope=scope,
        metric=metric,
    )


def test_format_display_ars() -> None:
    assert format_display_ars("21262335") == "21.262.335"
    assert format_display_ars("-14950948") == "-14.950.948"


def test_eeff_chunk_uses_idp_marker() -> None:
    claims = (
        _claim("2026-03-31", SCOPE_CONSOLIDADO, METRIC_NETO, "21262335"),
        _claim("2026-03-31", SCOPE_CONTROLANTE, METRIC_ATRIBUIBLE, "21259769"),
        _claim("2026-03-31", SCOPE_CONSOLIDADO, METRIC_BRUTO, "60144176"),
        _claim("2026-03-31", SCOPE_CONSOLIDADO, METRIC_OPERATIVO, "70223471"),
        _claim("2026-03-31", SCOPE_CONSOLIDADO, METRIC_IMPUESTO, "-14950948"),
        _claim("2026-03-31", SCOPE_CONSOLIDADO, METRIC_NCI, "2566"),
    )
    built = eeff_chunk(claims, "2026-03-31")
    assert built is not None
    content, keywords, questions = built
    assert MARKER in content
    assert "21.262.335" in content
    assert "21.259.769" in content
    assert "60.144.176" in content
    assert "70.223.471" in content
    assert "-14.950.948" in content
    assert "2.566" in content
    assert "RESULTADO BRUTO" in content
    assert "hechos_eeff.md" not in content
    joined_kw = " ".join(keywords).casefold()
    assert "resultado bruto" in joined_kw
    assert "no controlante" in joined_kw
    assert any("bruto" in q.casefold() for q in questions)


def test_upsert_replaces_graph_block() -> None:
    old = "--- Fichas Graph (claimprint) ---\nOLD\n--- Fin fichas Graph ---\n{knowledge}"
    text = upsert_idp_prompt(old, "NEW RULES")
    assert "OLD" not in text
    assert "Fichas IDP" in text
    assert "{knowledge}" in text


def test_strip_idp_prompt_removes_idp_and_graph() -> None:
    mixed = (
        f"{IDP_START}\nrules\n--- Fin fichas IDP ---\n"
        "--- Fichas Graph (claimprint) ---\nOLD\n--- Fin fichas Graph ---\n"
        "Eres un asistente.\n{knowledge}"
    )
    text = strip_idp_prompt(mixed)
    assert IDP_START not in text
    assert "Fichas Graph" not in text
    assert "Eres un asistente." in text
    assert "{knowledge}" in text


def test_is_inject_chunk_sees_graph_and_idp() -> None:
    assert is_inject_chunk(f"{MARKER} hello")
    assert is_inject_chunk(f"{MARKER_GRAPH} hello")
    assert not is_inject_chunk("plain chunk")


def test_prompt_lists_all_scopes() -> None:
    claims = (
        _claim("2026-03-31", SCOPE_CONSOLIDADO, METRIC_NETO, "21262335"),
        _claim("2026-03-31", "comunicado", "press_as_of_date", "2026-05-08", 1),
        _claim("2026-03-31", "presentacion", "presentation_ebitda", "72128", 12),
    )
    blob = prompt_lines(claims)
    assert "EEFF al 2026-03-31" in blob
    assert "consolidado|resultado_neto" in blob
    assert "Comunicado 2026-03-31" in blob
    assert "press_as_of_date" in blob
    assert "2026-05-08" in blob
    assert "Presentación 2026-03-31" in blob
    assert "presentation_ebitda" in blob


def test_idp_rules_cover_press_deck_memoria_and_ltm() -> None:
    blob = prompt_lines(())
    low = blob.casefold()
    assert "comunicado" in low
    assert "presentación" in low or "presentacion" in low
    assert "memoria" in low
    assert "margen" in low or "ltm" in low
    assert "no hay evidencia" in low
    assert "bruto" in low
    assert "no controlante" in low
