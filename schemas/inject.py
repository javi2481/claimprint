"""Format kernel claims for RAGFlow chunk + prompt inject. Not identity gold."""

from __future__ import annotations

import re
from collections.abc import Iterable

from schemas.claim import (
    METRIC_ATRIBUIBLE,
    METRIC_BRUTO,
    METRIC_EBT,
    METRIC_IMPUESTO,
    METRIC_NCI,
    METRIC_NETO,
    METRIC_OPERATIVO,
    SCOPE_CONSOLIDADO,
    SCOPE_CONTROLANTE,
    SCOPE_PRESENTATION,
    SCOPE_PRESS,
    Claim,
)
from schemas.classify import dedicated_financial_statement
from schemas.money import format_display_ars

MARKER = "Ficha IDP"
MARKER_GRAPH = "Ficha Graph EEFF"
# Prompt chrome. Keep "claimprint" in markers so a live RAGFlow chat
# from the old inject still matches on upsert.
IDP_START = "--- Fichas IDP (claimprint) ---"
IDP_END = "--- Fin fichas IDP ---"
GRAPH_START = "--- Fichas Graph (claimprint) ---"
GRAPH_END = "--- Fin fichas Graph ---"
SIDECAR_NAMES = ("hechos_eeff.md",)

MONEY_METRICS = {
    METRIC_NETO,
    METRIC_ATRIBUIBLE,
    METRIC_BRUTO,
    METRIC_OPERATIVO,
    METRIC_EBT,
    METRIC_IMPUESTO,
    METRIC_NCI,
    "presentation_ebitda",
}

# P&L neighbors injected into the EEFF document chunk (retrieval boost).
_EEFF_PNL: tuple[tuple[str, str, str], ...] = (
    (METRIC_BRUTO, "RESULTADO BRUTO", "resultado bruto"),
    (METRIC_OPERATIVO, "RESULTADO OPERATIVO", "resultado operativo"),
    (METRIC_EBT, "RESULTADO ANTES DEL IMPUESTO", "antes del impuesto"),
    (METRIC_IMPUESTO, "Impuesto a las ganancias", "impuesto a las ganancias"),
    (METRIC_NCI, "participación no controlante", "no controlante"),
)

IDP_RULES = (
    "Las «Fichas de este corpus» y los bloques «Ficha IDP» son la fuente de verdad "
    "numérica del kernel. Para resultado bruto / operativo / antes del impuesto / "
    "impuesto a las ganancias / participación no controlante / resultado neto del "
    "período, si la pregunta NO nombra presentación, comunicado ni memoria, usá "
    "siempre las cifras EEFF (scope consolidado|… o controlante|…) de la ficha — "
    "nunca los millones de una tabla de slides (Utilidad Bruta / Resultado "
    "Operativo del deck). "
    "Filas EEFF distintas (no intercambiables): "
    "(1) participación NO controlante → consolidado|resultado_no_controlante "
    "de la ficha (cifra chica). La pregunta «Resultado atribuible a la "
    "participación no controlante …» DEBE usar esa fila de la ficha — no "
    "abstengas y no uses el neto ni el controlante. "
    "(2) RESULTADO NETO DEL PERÍODO consolidado, si pide neto / el período / un "
    "trimestre sin decir controlante ni atribuible. "
    "(3) atribuible a la participación controlante / propietarios (sin «no "
    "controlante») → fila controlante. "
    "Si hay dos filas vecinas, no elijas la de al lado. Ignorá la columna del "
    "ejercicio anterior. Justificá con una cita del PDF del estado financiero "
    "(Show Quote). No cites un markdown auxiliar ni hechos_eeff.md. "
    "ABSTENER (única respuesta: «No hay evidencia en el corpus para responder.») "
    "sin inventar cifras del EEFF ni del deck — SOLO si la pregunta nombra "
    "explícitamente la fuente equivocada: "
    "(a) P&L / neto / bruto / operativo / impuesto «del comunicado»; "
    "(b) P&L / neto / bruto / operativo / impuesto / consolidado «de la "
    "presentación» o «del deck»; "
    "(c) resultado neto / P&L «de la memoria». "
    "No abstengas por la sola palabra «atribuible» ni por «no controlante» cuando "
    "la pregunta pide el EEFF. "
    "EBITDA en millones y margen EBITDA LTM de presentación vienen solo del "
    "deck; margen EBITDA LTM del comunicado es métrica del comunicado — no "
    "confundas esas dos. Si preguntan si coinciden los márgenes LTM de "
    "comunicado y presentación, buscá evidencia en ambos PDFs y respondé con la "
    "cifra común cuando ambos digan lo mismo."
)


def display_value(claim: Claim) -> str:
    if claim.metric in MONEY_METRICS:
        return format_display_ars(claim.value)
    return claim.value


def claim_of(
    claims: Iterable[Claim],
    *,
    period: str,
    scope: str,
    metric: str,
) -> Claim | None:
    for claim in claims:
        if claim.period == period and claim.scope == scope and claim.metric == metric:
            return claim
    return None


def needs_eeff_chunk(name: str) -> bool:
    return dedicated_financial_statement(name)


def eeff_chunk(claims: tuple[Claim, ...] | list[Claim], period: str) -> tuple[str, list[str], list[str]] | None:
    consolidado = claim_of(claims, period=period, scope=SCOPE_CONSOLIDADO, metric=METRIC_NETO)
    controlante = claim_of(claims, period=period, scope=SCOPE_CONTROLANTE, metric=METRIC_ATRIBUIBLE)
    if consolidado is None or controlante is None:
        return None
    cons = display_value(consolidado)
    ctrl = display_value(controlante)
    page = consolidado.source_page or 4
    lines = [
        f"{MARKER} — síntesis de la estructura de resultados consolidada, página {page}, "
        f"EEFF al {period}.",
    ]
    keywords = ["consolidado", "controlante", "RESULTADO NETO", "EEFF", cons, ctrl, period]
    questions = [
        f"Cuál es el RESULTADO NETO DEL PERÍODO al {period}",
        f"Resultado atribuible a la participación controlante al {period}",
        f"Cuál es el resultado bruto del EEFF al {period}",
        f"Resultado operativo EEFF al {period}",
        f"Impuesto a las ganancias EEFF al {period}",
        f"Participación no controlante EEFF al {period}",
    ]
    for metric, label, kw in _EEFF_PNL:
        row = claim_of(claims, period=period, scope=SCOPE_CONSOLIDADO, metric=metric)
        if row is None:
            continue
        shown = display_value(row)
        lines.append(f"{label} (estado consolidado EEFF): {shown}.")
        keywords.extend([kw, label, shown])
    nci = claim_of(claims, period=period, scope=SCOPE_CONSOLIDADO, metric=METRIC_NCI)
    nci_bit = ""
    if nci is not None:
        nci_shown = display_value(nci)
        nci_bit = (
            f" Participación NO controlante = {nci_shown} "
            f"(no confundir con controlante {ctrl} ni con neto {cons}). "
            f"Pregunta tipo «Resultado atribuible a la participación no "
            f"controlante» al {period} → {nci_shown}."
        )
        questions.append(
            f"Resultado atribuible a la participación no controlante al {period}"
        )
        keywords.extend(
            [
                "atribuible a la participación no controlante",
                "participación no controlante",
                nci_shown,
            ]
        )
    lines.append(f"RESULTADO NETO DEL PERÍODO (estado consolidado): {cons}.")
    lines.append(f"Resultado atribuible a la participación controlante: {ctrl}.")
    lines.append(
        f"Si la pregunta pide bruto / operativo / impuesto / no controlante / neto "
        f"del período sin nombrar presentación ni comunicado ni memoria, usá estas "
        f"cifras EEFF (no los millones del deck). Neto consolidado sin decir "
        f"controlante = {cons}; {ctrl} es la fila de al lado (controlante)."
        f"{nci_bit}"
    )
    return "\n".join(lines), keywords, questions


def _scope_bucket(scope: str | None) -> str:
    if scope in (SCOPE_CONSOLIDADO, SCOPE_CONTROLANTE):
        return "eeff"
    if scope == SCOPE_PRESS:
        return "comunicado"
    if scope == SCOPE_PRESENTATION:
        return "presentacion"
    return "otro"


def prompt_lines(claims: tuple[Claim, ...] | list[Claim]) -> str:
    rows = list(claims)
    if not rows:
        return IDP_RULES
    lines = [
        IDP_RULES,
        "Fichas de este corpus (EEFF = estado financiero; comunicado y presentación "
        "solo sus métricas propias — no mezclar P&L):",
    ]
    by_period: dict[str, list[Claim]] = {}
    for claim in rows:
        by_period.setdefault(claim.period, []).append(claim)
    for period in sorted(by_period):
        buckets: dict[str, list[Claim]] = {"eeff": [], "comunicado": [], "presentacion": [], "otro": []}
        for claim in by_period[period]:
            buckets[_scope_bucket(claim.scope)].append(claim)
        page = next(
            (c.source_page for c in buckets["eeff"] if c.source_page),
            next((c.source_page for c in by_period[period] if c.source_page), None),
        )
        page_bit = f", página {page}" if page else ""
        if buckets["eeff"]:
            bits = [f"{c.scope}|{c.metric} {display_value(c)}" for c in buckets["eeff"]]
            lines.append(f"- EEFF al {period}{page_bit}: " + "; ".join(bits) + ".")
        if buckets["comunicado"]:
            bits = [f"{c.metric} {display_value(c)}" for c in buckets["comunicado"]]
            lines.append(f"- Comunicado {period}: " + "; ".join(bits) + ".")
        if buckets["presentacion"]:
            bits = [f"{c.metric} {display_value(c)}" for c in buckets["presentacion"]]
            lines.append(f"- Presentación {period}: " + "; ".join(bits) + ".")
        if buckets["otro"]:
            bits = [f"{c.scope or '?'}|{c.metric or '?'} {display_value(c)}" for c in buckets["otro"]]
            lines.append(f"- Otros {period}: " + "; ".join(bits) + ".")
    return "\n".join(lines)


def strip_idp_prompt(system: str) -> str:
    text = system or ""
    text = re.sub(
        re.escape(IDP_START) + r".*?" + re.escape(IDP_END) + r"\n?",
        "",
        text,
        flags=re.S,
    )
    text = re.sub(
        re.escape(GRAPH_START) + r".*?" + re.escape(GRAPH_END) + r"\n?",
        "",
        text,
        flags=re.S,
    )
    text = re.sub(
        r"FICHAS GRAPH \(identidad.*?(?=\nEres un asistente|\nAquí está la base)",
        "",
        text,
        flags=re.S,
    )
    return text.strip()


def upsert_idp_prompt(system: str, block: str) -> str:
    wrapped = f"{IDP_START}\n{block}\n{IDP_END}"
    text = system or ""
    text = re.sub(
        re.escape(IDP_START) + r".*?" + re.escape(IDP_END) + r"\n?",
        "",
        text,
        flags=re.S,
    )
    text = re.sub(
        re.escape(GRAPH_START) + r".*?" + re.escape(GRAPH_END) + r"\n?",
        "",
        text,
        flags=re.S,
    )
    text = re.sub(
        r"FICHAS GRAPH \(identidad.*?(?=\nEres un asistente|\nAquí está la base)",
        "",
        text,
        flags=re.S,
    )
    if "{knowledge}" in text:
        return text.replace("{knowledge}", wrapped + "\n{knowledge}", 1)
    if text.strip():
        return wrapped + "\n" + text
    return (
        "Responde solo en español. Cita los fragmentos. Si no hay evidencia, usa la "
        "respuesta vacía. No inventes cifras.\n"
        f"{wrapped}\n"
        "Eres un asistente inteligente. Resume el contenido de la base de conocimiento "
        "para responder la pregunta. Enumera los datos de la base de conocimiento y "
        "responde con detalle. Cuando todo el contenido de la base de conocimiento sea "
        "irrelevante para la pregunta, tu respuesta debe incluir la frase "
        '"No hay evidencia suficiente en los documentos indexados para responder. '
        'No invento datos.". Las respuestas necesitan considerar el historial de chat.\n'
        "Aquí está la base de conocimiento:\n{knowledge}\n"
        "Esa es la base de conocimiento."
    )


def is_inject_chunk(text: str) -> bool:
    return MARKER in text or MARKER_GRAPH in text
