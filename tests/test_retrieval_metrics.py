"""Pure retrieval metrics: no HTTP, no RAGFlow."""

from schemas.retrieval_metrics import recall_at_k, mrr, score_case, summarize_arm
from schemas.rag_chat_score import score_chat_case, summarize_chat

EEFF = "BYMA_-_EEFF_31-03-2026_VF.pdf"
GOLD = [{"doc": EEFF, "page": 4}]


def test_chunk_to_hit_reads_positions() -> None:
    from schemas.ragflow_http import chunk_to_hit

    hit = chunk_to_hit(
        {
            "document_keyword": "BYMA_-_EEFF_31-03-2026_VF.pdf",
            "positions": [[4, 0, 0, 0]],
        }
    )
    assert hit == {"doc": "BYMA_-_EEFF_31-03-2026_VF.pdf", "page": 4}
    ranked = [(EEFF, 1), (EEFF, 4), ("other.pdf", 2)]
    gold = {(EEFF, 4)}
    assert recall_at_k(ranked, gold, 1) == 0.0
    assert recall_at_k(ranked, gold, 5) == 1.0
    assert mrr(ranked, gold) == 0.5


def test_score_case_from_dicts() -> None:
    ranked = [{"doc": EEFF, "page": 4}, {"doc": "press.pdf", "page": 2}]
    scores = score_case(ranked, GOLD)
    assert scores["recall@5"] == 1.0
    assert scores["recall@10"] == 1.0
    assert scores["mrr"] == 1.0


def test_summarize_arm() -> None:
    rows = [
        {"recall@5": 1.0, "recall@10": 1.0, "mrr": 1.0},
        {"recall@5": 0.0, "recall@10": 1.0, "mrr": 0.5},
    ]
    out = summarize_arm(rows)
    assert out["n"] == 2
    assert out["recall@5"] == 0.5
    assert out["recall@10"] == 1.0
    assert out["mrr"] == 0.75


def test_identity_chat_score() -> None:
    case = {
        "partition": "identity",
        "expected_value": "21262335",
        "expected_docs": [EEFF],
        "forbid_values": ["21259769"],
        "expected_abstain": False,
    }
    ok = score_chat_case(case, {"answer": "El neto es 21.262.335", "cited_docs": [EEFF]})
    assert ok["answer_value_match"] == 1.0
    assert ok["citation_doc_match"] == 1.0
    bad = score_chat_case(case, {"answer": "21259769", "cited_docs": [EEFF]})
    assert bad["answer_value_match"] == 0.0


def test_abstain_chat_score() -> None:
    case = {
        "partition": "abstention",
        "expected_value": None,
        "expected_docs": [],
        "forbid_values": ["21262335"],
        "expected_abstain": True,
    }
    ok = score_chat_case(
        case,
        {
            "answer": "No hay evidencia suficiente en los documentos indexados para responder. No invento datos.",
            "cited_docs": [],
            "abstained": False,
        },
    )
    assert ok["abstention_correct"] == 1.0
    assert ok["answer_value_match"] == 1.0
    assert ok["evidence_doc_match"] is None
    assert ok["citation_doc_match"] is None
    leak = score_chat_case(case, {"answer": "21262335", "cited_docs": []})
    assert leak["abstention_correct"] == 0.0
    assert leak["answer_value_match"] == 0.0


def test_false_abstain_fails_identity_and_narrative() -> None:
    identity = {
        "partition": "identity",
        "expected_value": "21262335",
        "expected_docs": [EEFF],
        "forbid_values": [],
        "expected_abstain": False,
    }
    scored = score_chat_case(
        identity,
        {"answer": "No hay evidencia en el corpus para responder.", "cited_docs": [EEFF]},
    )
    assert scored["abstention_correct"] == 0.0
    assert scored["answer_value_match"] == 0.0

    narrative = {
        "partition": "narrative",
        "expected_value": None,
        "expected_docs": [EEFF],
        "forbid_values": [],
        "expected_abstain": False,
    }
    scored_n = score_chat_case(
        narrative,
        {"answer": "No hay evidencia en el corpus para responder.", "cited_docs": [EEFF]},
    )
    assert scored_n["abstention_correct"] == 0.0
    assert scored_n["answer_value_match"] == 0.0


def test_summarize_chat_skips_na_retrieval() -> None:
    scores = [
        {"evidence_doc_match": 1.0, "answer_value_match": 1.0, "citation_doc_match": 1.0, "abstention_correct": 1.0},
        {"evidence_doc_match": None, "answer_value_match": 1.0, "citation_doc_match": None, "abstention_correct": 1.0},
        {"evidence_doc_match": 0.0, "answer_value_match": 0.0, "citation_doc_match": 0.0, "abstention_correct": 0.0},
    ]
    out = summarize_chat(scores)
    assert out["n"] == 3
    assert out["evidence_doc_match"] == 0.5
    assert out["citation_doc_match"] == 0.5
    assert out["abstention_correct"] == round(2 / 3, 4)
    assert out["answer_value_match"] == round(2 / 3, 4)


def test_chunk_to_hit_without_page_returns_none() -> None:
    from schemas.ragflow_http import chunk_to_hit

    assert chunk_to_hit({"document_keyword": "x.pdf"}) is None
