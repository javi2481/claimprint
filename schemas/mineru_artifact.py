"""MinerU content sidecars: spans with bbox from RAGFlow chunks or MinerU content_list."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from schemas.parse_artifact import FIXTURES

CONTENT_VERSION = "content_v1"
BBOX_MINERU_1000 = "mineru_1000"
BBOX_RAGFLOW_PAGE = "ragflow_page"


def content_path(pdf: Path, fixtures: Path | None = None) -> Path:
    folder = fixtures or FIXTURES
    return folder / f"{pdf.stem}.content.json"


@dataclass(frozen=True)
class ContentSpan:
    page: int
    text: str
    type: str
    bbox_norm: tuple[float, float, float, float] | None
    bbox_raw: tuple[float, float, float, float] | None
    bbox_space: str | None


@dataclass(frozen=True)
class ContentSidecar:
    version: str
    source: str
    pdf_name: str
    spans: tuple[ContentSpan, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "source": self.source,
            "pdf_name": self.pdf_name,
            "spans": [
                {
                    "page": span.page,
                    "text": span.text,
                    "type": span.type,
                    "bbox_raw": list(span.bbox_raw) if span.bbox_raw else None,
                    "bbox_norm": list(span.bbox_norm) if span.bbox_norm else None,
                    "bbox_space": span.bbox_space,
                }
                for span in self.spans
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ContentSidecar:
        spans: list[ContentSpan] = []
        for row in payload.get("spans") or []:
            if not isinstance(row, dict):
                continue
            bbox_raw = _tuple4(row.get("bbox_raw"))
            bbox_norm = _tuple4(row.get("bbox_norm"))
            spans.append(
                ContentSpan(
                    page=int(row.get("page") or 0),
                    text=str(row.get("text") or ""),
                    type=str(row.get("type") or "text"),
                    bbox_norm=bbox_norm,
                    bbox_raw=bbox_raw,
                    bbox_space=row.get("bbox_space"),
                )
            )
        return cls(
            version=str(payload.get("version") or CONTENT_VERSION),
            source=str(payload.get("source") or "unknown"),
            pdf_name=str(payload.get("pdf_name") or ""),
            spans=tuple(spans),
        )


def _tuple4(raw: object) -> tuple[float, float, float, float] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) < 4:
        return None
    try:
        return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))
    except (TypeError, ValueError):
        return None


def _norm_from_mineru_1000(bbox: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    return tuple(min(1.0, max(0.0, v / 1000.0)) for v in bbox)  # type: ignore[return-value]


def _norm_from_ragflow_page(
    bbox: tuple[float, float, float, float],
    page_max: tuple[float, float],
) -> tuple[float, float, float, float]:
    max_x, max_y = page_max
    x0, y0, x1, y1 = bbox
    if max_x <= 0 or max_y <= 0:
        return bbox
    return (x0 / max_x, y0 / max_y, x1 / max_x, y1 / max_y)


def spans_from_content_list(blocks: list[dict[str, Any]], *, pdf_name: str) -> ContentSidecar:
    spans: list[ContentSpan] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        text = str(block.get("text") or "").strip()
        bbox = _tuple4(block.get("bbox"))
        if not text and bbox is None:
            continue
        page = int(block.get("page_idx") or 0) + 1
        bbox_norm = _norm_from_mineru_1000(bbox) if bbox else None
        spans.append(
            ContentSpan(
                page=page,
                text=text,
                type=str(block.get("type") or "text"),
                bbox_norm=bbox_norm,
                bbox_raw=bbox,
                bbox_space=BBOX_MINERU_1000 if bbox else None,
            )
        )
    return ContentSidecar(
        version=CONTENT_VERSION,
        source="mineru_api",
        pdf_name=pdf_name,
        spans=tuple(spans),
    )


def spans_from_ragflow_chunks(chunks: list[dict[str, Any]], *, pdf_name: str) -> ContentSidecar:
    raw_rows: list[tuple[int, tuple[float, float, float, float], str]] = []
    for chunk in chunks:
        text = (chunk.get("content") or chunk.get("content_with_weight") or "").strip()
        if not text:
            continue
        for pos in chunk.get("positions") or []:
            if not isinstance(pos, (list, tuple)) or len(pos) < 5:
                continue
            try:
                page = int(pos[0])
                x0, x1, y0, y1 = float(pos[1]), float(pos[2]), float(pos[3]), float(pos[4])
            except (TypeError, ValueError, IndexError):
                continue
            raw_rows.append((page, (x0, y0, x1, y1), text))

    page_max: dict[int, tuple[float, float]] = {}
    for page, (x0, y0, x1, y1), _ in raw_rows:
        max_x, max_y = page_max.get(page, (0.0, 0.0))
        page_max[page] = (max(max_x, x1), max(max_y, y1))

    spans: list[ContentSpan] = []
    for page, bbox, text in raw_rows:
        bbox_norm = _norm_from_ragflow_page(bbox, page_max.get(page, (1.0, 1.0)))
        spans.append(
            ContentSpan(
                page=page,
                text=text,
                type="ragflow_chunk",
                bbox_norm=bbox_norm,
                bbox_raw=bbox,
                bbox_space=BBOX_RAGFLOW_PAGE,
            )
        )
    return ContentSidecar(
        version=CONTENT_VERSION,
        source="ragflow_chunks",
        pdf_name=pdf_name,
        spans=tuple(spans),
    )


def write_content_sidecar(pdf: Path, sidecar: ContentSidecar, fixtures: Path | None = None) -> Path:
    dest = content_path(pdf, fixtures)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(sidecar.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dest


def load_content_sidecar(pdf: Path, fixtures: Path | None = None) -> ContentSidecar | None:
    path = content_path(pdf, fixtures)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return ContentSidecar.from_dict(payload)


def spans_on_page(sidecar: ContentSidecar, page: int) -> tuple[ContentSpan, ...]:
    return tuple(span for span in sidecar.spans if span.page == page)
