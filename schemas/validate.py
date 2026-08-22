"""Accept or reject a filled schema. Abstain = do not inject."""

from __future__ import annotations

from schemas.financial_statement import FinancialStatement


def reject_financial_statement(row: FinancialStatement) -> str | None:
    """Return a reason to abstain, or None if the identity contract holds."""
    if not (row.period or "").strip():
        return "missing period"
    cons = row.net_income_consolidated
    ctrl = row.net_income_attributable_to_parent
    if cons is None or ctrl is None or str(cons).strip() == "" or str(ctrl).strip() == "":
        return "missing consolidado or controlante"
    if cons == ctrl:
        return "consolidado equals controlante"
    ignore = row.prior_period_amount_to_ignore
    if ignore and cons == ignore:
        return "consolidado matches prior-period column"
    return None
