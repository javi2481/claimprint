"""Local JSON claim cache for the CLI. Evals still extract; this is not overlay gold."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from schemas.claim import Claim
from schemas.corpus import SAMPLES, extract_claims_from_dir
from schemas.parse_artifact import parse_sha256

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / "outputs" / "claims.json"
STORE_VERSION = 4

ExtractFn = Callable[[Path], tuple[Claim, ...]]


def pdf_fingerprint(directory: Path, fixtures: Path | None = None) -> dict:
    folder = directory.resolve()
    sources = []
    for pdf in sorted(folder.glob("*.pdf")):
        stat = pdf.stat()
        sources.append(
            {
                "name": pdf.name,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "parse_sha256": parse_sha256(pdf, fixtures),
            }
        )
    return {"directory": str(folder), "sources": sources}


def _bbox_from_row(raw: object) -> tuple[float, float, float, float] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) < 4:
        return None
    try:
        return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))
    except (TypeError, ValueError):
        return None


def _claims_from_payload(raw: list[object]) -> tuple[Claim, ...] | None:
    out: list[Claim] = []
    for row in raw:
        if not isinstance(row, dict):
            return None
        try:
            out.append(
                Claim(
                    identity_key=str(row["identity_key"]),
                    value=str(row["value"]),
                    period=str(row["period"]),
                    source_page=row.get("source_page"),
                    source_text=row.get("source_text"),
                    issuer=row.get("issuer"),
                    scope=row.get("scope"),
                    metric=row.get("metric"),
                    document_id=row.get("document_id"),
                    parse_artifact_hash=row.get("parse_artifact_hash") or row.get("source_hash"),
                    source_bbox=_bbox_from_row(row.get("source_bbox")),
                )
            )
        except (KeyError, TypeError):
            return None
    return tuple(out)


def _read_store(path: Path, fingerprint: dict) -> tuple[Claim, ...] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("version") != STORE_VERSION:
        return None
    if payload.get("directory") != fingerprint["directory"]:
        return None
    if payload.get("sources") != fingerprint["sources"]:
        return None
    raw = payload.get("claims")
    if not isinstance(raw, list):
        return None
    return _claims_from_payload(raw)


def _write_store(path: Path, fingerprint: dict, claims: tuple[Claim, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": STORE_VERSION,
        "directory": fingerprint["directory"],
        "sources": fingerprint["sources"],
        "claims": [asdict(row) for row in claims],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_claims(
    directory: Path | None = None,
    *,
    store_path: Path | None = None,
    force: bool = False,
    extract: ExtractFn = extract_claims_from_dir,
    fixtures: Path | None = None,
) -> tuple[tuple[Claim, ...], bool]:
    folder = (directory or SAMPLES).resolve()
    path = store_path or DEFAULT_STORE
    fingerprint = pdf_fingerprint(folder, fixtures)
    if not force:
        cached = _read_store(path, fingerprint)
        if cached is not None:
            return cached, True
    claims = extract(folder)
    _write_store(path, fingerprint, claims)
    return claims, False
