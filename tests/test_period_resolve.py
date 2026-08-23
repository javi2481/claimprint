"""Content-first quarter period resolution."""

from __future__ import annotations

from schemas.period_resolve import LABEL_1T26, PERIOD_1T26, resolve_quarter_period


def test_front_matter_wins_over_wrong_filename() -> None:
    front = "Presentación de Resultados\n1° TRIMESTRE 2026 (1T26)\n8 de mayo de 2026"
    row = resolve_quarter_period(front_matter=front, filename="deck_sin_token.pdf")
    assert row == (PERIOD_1T26, LABEL_1T26)


def test_press_period_from_march_end_date() -> None:
    front = (
        "BYMA anuncia resultados\n"
        "reportó resultados para el período finalizado el 31 de marzo de 2026"
    )
    row = resolve_quarter_period(front_matter=front, filename="comunicado.pdf")
    assert row == (PERIOD_1T26, LABEL_1T26)


def test_filename_fallback_when_body_silent() -> None:
    row = resolve_quarter_period(front_matter="", filename="Presentacion_de_resultados_BYMA-2T26.pdf")
    assert row is not None
    assert row[0] == "2026-06-30"
