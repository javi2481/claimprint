"""CLI claim cache: hit skips extract; evals still extract on their own."""

from __future__ import annotations

import json
from pathlib import Path

from schemas.claim import Claim, identity_key
from schemas.store import load_claims

SAMPLE = Claim(
    identity_key=identity_key("BYMA", "2026-03-31", "consolidado", "resultado_neto"),
    value="21262335",
    period="2026-03-31",
    source_page=4,
    source_text="resultado neto 21.262.335",
    issuer="BYMA",
    scope="consolidado",
    metric="resultado_neto",
)


def _touch_pdf(folder: Path, name: str, payload: bytes = b"%PDF-1.4\n") -> Path:
    path = folder / name
    path.write_bytes(payload)
    return path


def test_second_load_skips_extract(tmp_path: Path) -> None:
    folder = tmp_path / "pdfs"
    folder.mkdir()
    _touch_pdf(folder, "a.pdf")
    store = tmp_path / "claims.json"
    calls = {"n": 0}

    def extract(directory: Path) -> tuple[Claim, ...]:
        calls["n"] += 1
        assert directory == folder.resolve()
        return (SAMPLE,)

    first, cached_first = load_claims(folder, store_path=store, extract=extract)
    second, cached_second = load_claims(folder, store_path=store, extract=extract)
    assert first == (SAMPLE,)
    assert second == first
    assert cached_first is False
    assert cached_second is True
    assert calls["n"] == 1


def test_stale_pdf_reextracts(tmp_path: Path) -> None:
    folder = tmp_path / "pdfs"
    folder.mkdir()
    pdf = _touch_pdf(folder, "a.pdf")
    store = tmp_path / "claims.json"
    calls = {"n": 0}

    def extract(directory: Path) -> tuple[Claim, ...]:
        calls["n"] += 1
        return (SAMPLE,)

    load_claims(folder, store_path=store, extract=extract)
    pdf.write_bytes(b"%PDF-1.4\nbigger")
    _, cached = load_claims(folder, store_path=store, extract=extract)
    assert cached is False
    assert calls["n"] == 2


def test_force_reextracts_fresh_store(tmp_path: Path) -> None:
    folder = tmp_path / "pdfs"
    folder.mkdir()
    _touch_pdf(folder, "a.pdf")
    store = tmp_path / "claims.json"
    calls = {"n": 0}

    def extract(directory: Path) -> tuple[Claim, ...]:
        calls["n"] += 1
        return (SAMPLE,)

    load_claims(folder, store_path=store, extract=extract)
    _, cached = load_claims(folder, store_path=store, force=True, extract=extract)
    assert cached is False
    assert calls["n"] == 2


def test_corrupt_json_is_a_miss(tmp_path: Path) -> None:
    folder = tmp_path / "pdfs"
    folder.mkdir()
    _touch_pdf(folder, "a.pdf")
    store = tmp_path / "claims.json"
    store.write_text("{not json", encoding="utf-8")
    calls = {"n": 0}

    def extract(directory: Path) -> tuple[Claim, ...]:
        calls["n"] += 1
        return (SAMPLE,)

    claims, cached = load_claims(folder, store_path=store, extract=extract)
    assert cached is False
    assert claims == (SAMPLE,)
    assert calls["n"] == 1
    payload = json.loads(store.read_text(encoding="utf-8"))
    assert payload["version"] == 4
    assert payload["claims"][0]["value"] == "21262335"


def test_stale_parse_reextracts(tmp_path: Path) -> None:
    folder = tmp_path / "pdfs"
    folder.mkdir()
    _touch_pdf(folder, "a.pdf")
    fixtures = tmp_path / "mineru"
    fixtures.mkdir()
    parse = fixtures / "a.md"
    parse.write_text("<!-- page: 1 -->\nold\n", encoding="utf-8")
    store = tmp_path / "claims.json"
    calls = {"n": 0}

    def extract(directory: Path) -> tuple[Claim, ...]:
        calls["n"] += 1
        return (SAMPLE,)

    load_claims(folder, store_path=store, extract=extract, fixtures=fixtures)
    parse.write_text("<!-- page: 1 -->\nnew\n", encoding="utf-8")
    _, cached = load_claims(folder, store_path=store, extract=extract, fixtures=fixtures)
    assert cached is False
    assert calls["n"] == 2


def test_eval_harnesses_do_not_import_store() -> None:
    root = Path(__file__).resolve().parent
    for name in ("test_evals.py", "test_evals_v2.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert "schemas.store" not in text
        assert "extract_claims_from_dir" in text
