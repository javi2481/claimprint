"""Extract typed claims from a directory of PDFs. No RAGFlow."""

from __future__ import annotations

from pathlib import Path

from schemas.claim import Claim, claims_from_financial_statement
from schemas.extract import extract_financial_statement
from schemas.finance_lines import claims_from_pnl_lines
from schemas.parse_artifact import load_parse, page_text
from schemas.press_release import claims_from_press_release, extract_press_release
from schemas.provenance import enrich_claim_provenance
from schemas.results_presentation import (
    claims_from_results_presentation,
    extract_results_presentation,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "docs" / "archivos_muestra"


def _with_provenance(pdf: Path, claims: tuple[Claim, ...]) -> tuple[Claim, ...]:
    return tuple(enrich_claim_provenance(claim, pdf) for claim in claims)


def extract_claims_from_dir(directory: Path | None = None) -> tuple[Claim, ...]:
    folder = directory or SAMPLES
    out: list[Claim] = []
    for pdf in sorted(folder.glob("*.pdf")):
        row = extract_financial_statement(pdf)
        if row is not None:
            out.extend(_with_provenance(pdf, claims_from_financial_statement(row)))
            if row.source_page:
                artifact = load_parse(pdf)
                if artifact is not None:
                    text = page_text(artifact, row.source_page)
                    out.extend(_with_provenance(pdf, claims_from_pnl_lines(text, row)))
            continue
        press = extract_press_release(pdf)
        if press is not None:
            out.extend(_with_provenance(pdf, claims_from_press_release(press)))
            continue
        deck = extract_results_presentation(pdf)
        if deck is not None:
            out.extend(_with_provenance(pdf, claims_from_results_presentation(deck)))
    return tuple(out)
