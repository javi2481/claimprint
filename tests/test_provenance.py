"""Provenance: document_id + bbox from MinerU sidecars."""

from __future__ import annotations

from pathlib import Path

from schemas.claim import METRIC_NETO, SCOPE_CONSOLIDADO, Claim, identity_key
from schemas.corpus import SAMPLES, extract_claims_from_dir
from schemas.mineru_artifact import content_path, spans_from_ragflow_chunks
from schemas.provenance import enrich_claim_provenance, match_bbox, pdf_document_id


def test_pdf_document_id_is_stable(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 same bytes")
    first = pdf_document_id(pdf)
    pdf.write_bytes(b"%PDF-1.4 same bytes")
    assert pdf_document_id(pdf) == first
    pdf.write_bytes(b"%PDF-1.4 other")
    assert pdf_document_id(pdf) != first


def test_match_bbox_prefers_source_text_on_page() -> None:
    sidecar = spans_from_ragflow_chunks(
        [
            {
                "content": "RESULTADO NETO DEL PERÍODO 21.262.335",
                "positions": [[4, 100, 500, 200, 240]],
            },
            {
                "content": "otro bloque sin cifra relevante",
                "positions": [[4, 100, 500, 300, 340]],
            },
        ],
        pdf_name="eeff.pdf",
    )
    bbox = match_bbox(
        sidecar,
        source_text="RESULTADO NETO DEL PERÍODO",
        page=4,
        value="21262335",
    )
    assert bbox is not None
    assert bbox == sidecar.spans[0].bbox_norm


def test_match_bbox_returns_none_without_evidence(tmp_path: Path) -> None:
    sidecar = spans_from_ragflow_chunks(
        [{"content": "sin cifras", "positions": [[1, 0, 100, 0, 20]]}],
        pdf_name="x.pdf",
    )
    path = content_path(tmp_path / "x.pdf", fixtures=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(__import__("json").dumps(sidecar.to_dict()), encoding="utf-8")
    assert match_bbox(path, source_text="inventado", page=1, value="999") is None


def test_eeff_neto_consolidado_has_bbox_or_honest_null() -> None:
    pdf = SAMPLES / "BYMA_-_EEFF_31-03-2026_VF.pdf"
    claims = extract_claims_from_dir(SAMPLES)
    neto = next(
        c
        for c in claims
        if c.scope == SCOPE_CONSOLIDADO and c.metric == METRIC_NETO and c.period == "2026-03-31"
    )
    assert neto.document_id == pdf_document_id(pdf)
    assert neto.source_bbox is not None
    assert len(neto.source_bbox) == 4
    assert all(0.0 <= v <= 1.0 for v in neto.source_bbox)


def test_enrich_claim_never_invents_bbox(tmp_path: Path) -> None:
    pdf = tmp_path / "empty.pdf"
    pdf.write_bytes(b"%PDF")
    claim = Claim(
        identity_key=identity_key("X", "2026-03-31", SCOPE_CONSOLIDADO, METRIC_NETO),
        value="1",
        period="2026-03-31",
        source_page=1,
        source_text="no existe en sidecar",
        issuer="X",
        scope=SCOPE_CONSOLIDADO,
        metric=METRIC_NETO,
    )
    enriched = enrich_claim_provenance(claim, pdf, fixtures=tmp_path)
    assert enriched.document_id
    assert enriched.source_bbox is None
