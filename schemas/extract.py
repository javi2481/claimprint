"""Layer 1: recipe page select + deterministic FinancialStatement fill."""

from __future__ import annotations

import re
from pathlib import Path

from schemas.catalog import Recipe, load_recipes
from schemas.classify import UNKNOWN, classify_artifact
from schemas.financial_statement import FinancialStatement
from schemas.money import digits_ars
from schemas.parse_artifact import ParseArtifact, fold, load_parse, page_text
from schemas.validate import reject_financial_statement

AMOUNT_RE = re.compile(r"\d{1,3}(?:\.\d{3})+")
DATE_RE = re.compile(
    r"(\d{1,2})\s+DE\s+(ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|"
    r"AGOSTO|SEPTIEMBRE|SETIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)\s+DE\s+(\d{4})",
    re.IGNORECASE,
)
MONTHS = {
    "enero": "01",
    "febrero": "02",
    "marzo": "03",
    "abril": "04",
    "mayo": "05",
    "junio": "06",
    "julio": "07",
    "agosto": "08",
    "septiembre": "09",
    "setiembre": "09",
    "octubre": "10",
    "noviembre": "11",
    "diciembre": "12",
}


def select_page(
    pdf: Path,
    keywords: tuple[str, ...],
    max_pages: int = 24,
    artifact: ParseArtifact | None = None,
) -> int | None:
    """First page whose folded text contains any keyword — deterministic routing, not layout ranking."""
    parsed = artifact if artifact is not None else load_parse(pdf)
    if parsed is None:
        return None
    folded_keys = tuple(fold(k) for k in keywords if k.strip())
    empty_run = 0
    for number, text in parsed.pages:
        if number > max_pages:
            break
        if not text.strip():
            empty_run += 1
            if empty_run >= 2:
                break
            continue
        empty_run = 0
        blob = fold(text)
        if any(key in blob for key in folded_keys):
            return number
    return None


def _amounts(line: str) -> list[str]:
    found: list[str] = []
    for raw in AMOUNT_RE.findall(line):
        digits = digits_ars(raw)
        if digits:
            found.append(digits)
    return found


def _label_before_amount(line: str) -> str:
    match = AMOUNT_RE.search(line)
    label = line[: match.start()] if match else line
    return " ".join(label.split())


def _is_consolidado_line(line: str) -> bool:
    u = fold(line)
    if "resultado neto del periodo" not in u:
        return False
    if "atribuible" in u or "controlante" in u:
        return False
    if "accion" in u:
        return False
    return True


def _is_controlante_line(line: str) -> bool:
    u = fold(line)
    if "atribuible" not in u or "controlante" not in u:
        return False
    if "no controlante" in u:
        return False
    if "accionistas" in u:
        return False
    return True


def _period_from_text(text: str) -> str | None:
    match = DATE_RE.search(text)
    if not match:
        return None
    day = int(match.group(1))
    month = MONTHS[fold(match.group(2))]
    year = match.group(3)
    return f"{year}-{month}-{day:02d}"


def _issuer_from_text(text: str, filename: str) -> str | None:
    blob = fold(text) + " " + fold(filename)
    if "bolsas y mercados argentinos" in blob or "byma" in blob:
        return "BYMA"
    return None


def fill_financial_statement(page_text: str, *, source_page: int, filename: str) -> FinancialStatement | None:
    consolidado_line = ""
    controlante_line = ""
    for raw in page_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _is_consolidado_line(line) and not consolidado_line:
            consolidado_line = line
        elif _is_controlante_line(line) and not controlante_line:
            controlante_line = line
    if not consolidado_line or not controlante_line:
        return None
    cons_amts = _amounts(consolidado_line)
    ctrl_amts = _amounts(controlante_line)
    if not cons_amts or not ctrl_amts:
        return None
    consolidado = cons_amts[0]
    controlante = ctrl_amts[0]
    page_digits = "".join(ch for ch in page_text if ch.isdigit())
    if consolidado not in page_digits or controlante not in page_digits:
        return None
    period = _period_from_text(page_text)
    if not period:
        return None
    issuer = _issuer_from_text(page_text, filename)
    if not issuer:
        return None
    prior = cons_amts[1] if len(cons_amts) > 1 else None
    return FinancialStatement(
        issuer=issuer,
        period=period,
        net_income_consolidated=consolidado,
        net_income_attributable_to_parent=controlante,
        source_page=source_page,
        source_text_consolidado=_label_before_amount(consolidado_line) or "RESULTADO NETO DEL PERÍODO",
        source_text_controlante=_label_before_amount(controlante_line)
        or "Resultado atribuible a la participación controlante",
        prior_period_amount_to_ignore=prior,
    )


def extract_financial_statement(pdf: Path, recipes: dict[str, Recipe] | None = None) -> FinancialStatement | None:
    catalog = recipes if recipes is not None else load_recipes()
    artifact = load_parse(pdf)
    if artifact is None:
        return None
    recipe_id = classify_artifact(artifact, tuple(catalog))
    if recipe_id == UNKNOWN:
        return None
    recipe = catalog.get(recipe_id)
    if recipe is None or not recipe.extract:
        return None
    if recipe.id != "financial_statement":
        return None
    page = select_page(pdf, recipe.page_select_keywords, artifact=artifact)
    if page is None:
        return None
    text = page_text(artifact, page)
    row = fill_financial_statement(text, source_page=page, filename=pdf.name)
    if row is None:
        return None
    if reject_financial_statement(row):
        return None
    return row
