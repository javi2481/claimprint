# Spec delta: mineru-provenance

## Requirement: Rich MinerU sidecar

Each sample PDF MUST have a committed `fixtures/mineru/{stem}.content.json` derived from
MinerU `content_list` or RAGFlow chunk positions.

## Requirement: Optional claim bbox

WHEN a claim has `source_text` and a matching content block exists on `source_page`
THEN `source_bbox` MAY be set as normalized `[x0,y0,x1,y1]`.
WHEN no match exists THEN `source_bbox` MUST be null — MUST NOT invent coordinates.

### Scenario: EEFF neto consolidado 1T26

- GIVEN `BYMA_-_EEFF_31-03-2026_VF.pdf` sidecar and claim value `21262335`
- WHEN the projector runs
- THEN `document_id` MUST be stable sha256 of the PDF file
- AND `source_bbox` MUST be non-null only if a content block contains that value or line text
