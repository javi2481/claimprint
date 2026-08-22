"""Score rag_chat_v1 dumps. Value containment; abstain; citation docs. No RAGFlow."""

from __future__ import annotations

from collections.abc import Sequence

EMPTY_HINTS = (
    "no hay evidencia",
    "no invento",
    "no cuento con",
)


def _digits(text: str) -> str:
    return "".join(ch for ch in text if ch.isdigit())


def cited_ok(cited: Sequence[str], expected_docs: Sequence[str]) -> bool:
    if not expected_docs:
        return True
    have = {name.casefold() for name in cited}
    return any(doc.casefold() in have for doc in expected_docs)


def looks_abstained(answer: str, flagged: bool) -> bool:
    if flagged:
        return True
    blob = " ".join(answer.casefold().split())
    return any(hint in blob for hint in EMPTY_HINTS)


def score_chat_case(case: dict, run: dict) -> dict:
    """Per-case scores for the small chat pilot.

    - ``answer_value_match``: **exact-value containment** (not semantic accuracy). For
      identity/comparison, pass if ``expected_value`` appears in the answer
      digits/compact text, no ``forbid_values`` leak, and the model did not
      abstain. Narrative has no gold number (retrieval + no abstain + no leak).
    - ``abstention_correct``: 1 iff the model did what gold requires on abstain vs
      answer (abstain when ``expected_abstain``, otherwise must not abstain).
    - ``evidence_doc_match`` / ``citation_doc_match``: scored only when the case expects docs;
      abstain-only cases return ``None`` so they do not inflate averages.
    """
    partition = str(case.get("partition") or "")
    answer = str(run.get("answer") or "")
    cited = [str(x) for x in (run.get("cited_docs") or [])]
    abstained = looks_abstained(answer, bool(run.get("abstained")))
    expected_docs = [str(x) for x in (case.get("expected_docs") or [])]
    expected_value = case.get("expected_value")
    forbid = [str(x) for x in (case.get("forbid_values") or [])]
    want_abstain = bool(case.get("expected_abstain"))
    compact = answer.replace(".", "").replace(",", "").replace(" ", "")
    digit_blob = _digits(answer)
    leaked = any(val and (val in compact or val in digit_blob) for val in forbid)

    if want_abstain:
        ok = abstained and not leaked
        return {
            "evidence_doc_match": None,
            "answer_value_match": 1.0 if ok else 0.0,
            "citation_doc_match": None,
            "abstention_correct": 1.0 if ok else 0.0,
        }

    retrieval = cited_ok(cited, expected_docs)
    citation = retrieval and not any("hechos_eeff" in name.casefold() for name in cited)
    if partition == "comparison":
        retrieval = all(cited_ok(cited, [doc]) for doc in expected_docs) if expected_docs else True
        citation = retrieval

    # False abstain fails abstention; answering when required passes it.
    abstention = 0.0 if abstained else 1.0

    if partition == "narrative":
        ok = (not abstained) and not leaked and retrieval
        return {
            "evidence_doc_match": 1.0 if retrieval else 0.0,
            "answer_value_match": 1.0 if ok else 0.0,
            "citation_doc_match": 1.0 if citation else 0.0,
            "abstention_correct": abstention,
        }

    # Exact-value containment (pilot-sized; not full-answer accuracy).
    value_ok = expected_value is None or str(expected_value) in compact or str(expected_value) in digit_blob
    ok = value_ok and not leaked and not abstained
    return {
        "evidence_doc_match": 1.0 if retrieval else 0.0,
        "answer_value_match": 1.0 if ok else 0.0,
        "citation_doc_match": 1.0 if citation else 0.0,
        "abstention_correct": abstention,
    }


def _mean(values: Sequence[float | None]) -> float:
    present = [v for v in values if v is not None]
    if not present:
        return 0.0
    return round(sum(present) / len(present), 4)


def summarize_chat(scores: Sequence[dict]) -> dict:
    if not scores:
        return {"evidence_doc_match": 0.0, "answer_value_match": 0.0, "citation_doc_match": 0.0, "abstention_correct": 0.0, "n": 0}
    return {
        "evidence_doc_match": _mean([s.get("evidence_doc_match") for s in scores]),
        "answer_value_match": _mean([s.get("answer_value_match") for s in scores]),
        "citation_doc_match": _mean([s.get("citation_doc_match") for s in scores]),
        "abstention_correct": _mean([s.get("abstention_correct") for s in scores]),
        "n": len(scores),
    }
