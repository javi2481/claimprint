#!/usr/bin/env python3
"""Materialize MinerU parse artifacts for the kernel.

Default: export RAGFlow demo_4 chunks (dataset already parsed; no /file_parse).
`--bootstrap-layout`: write page-marked text from poppler when the demo is down.
`--with-content`: also write fixtures/mineru/<stem>.content.json (bbox spans).
The kernel never calls this; it only reads fixtures/mineru/*.md (+ optional *.content.json).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "docs" / "archivos_muestra"
sys.path.insert(0, str(ROOT))

from schemas.mineru_artifact import (  # noqa: E402
    spans_from_content_list,
    spans_from_ragflow_chunks,
    write_content_sidecar,
)
from schemas.parse_artifact import FIXTURES, artifact_path  # noqa: E402
from schemas.ragflow_http import load_env, token_from_mysql  # noqa: E402

API = os.environ.get("RAGFLOW_URL", "http://127.0.0.1/api/v1").rstrip("/")
MINERU_API = os.environ.get("MINERU_APISERVER", "http://127.0.0.1:8000").rstrip("/")
PAGE_POS = re.compile(r"page[^\d]{0,8}(\d+)", re.IGNORECASE)


def api(method: str, path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        method=method,
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"error: {method} {path} -> {exc.code} {body[:500]}") from exc


def rows_of(payload: dict, *keys: str) -> list:
    data = payload.get("data") or []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in keys:
            if isinstance(data.get(key), list):
                return data[key]
    return []


def list_chunks(ds_id: str, doc_id: str, token: str) -> list:
    chunks: list = []
    page = 1
    while page <= 50:
        body = api(
            "GET",
            f"/datasets/{ds_id}/documents/{doc_id}/chunks?page={page}&page_size=100",
            token,
        )
        batch = rows_of(body, "chunks")
        chunks.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return chunks


def _chunk_page(chunk: dict, fallback: int) -> int:
    positions = chunk.get("positions") or []
    if positions and isinstance(positions[0], (list, tuple)) and positions[0]:
        try:
            return int(positions[0][0])
        except (TypeError, ValueError, IndexError):
            pass
    blob = json.dumps(chunk.get("positions") or "")
    match = PAGE_POS.search(blob)
    if match:
        return int(match.group(1))
    return fallback


def markdown_from_chunks(chunks: list) -> str:
    by_page: dict[int, list[str]] = {}
    for idx, chunk in enumerate(chunks, start=1):
        text = (chunk.get("content") or chunk.get("content_with_weight") or "").strip()
        if not text:
            continue
        page = _chunk_page(chunk, idx)
        by_page.setdefault(page, []).append(text)
    if not by_page:
        return ""
    parts: list[str] = []
    for page in sorted(by_page):
        parts.append(f"<!-- page: {page} -->")
        parts.append("\n\n".join(by_page[page]))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def pdf_page_count(pdf: Path) -> int:
    proc = subprocess.run(
        ["pdfinfo", str(pdf)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    for line in proc.stdout.splitlines():
        if line.lower().startswith("pages:"):
            return int(line.split(":", 1)[1].strip())
    return 0


def bootstrap_layout(pdf: Path) -> str:
    count = pdf_page_count(pdf)
    if count < 1:
        raise SystemExit(f"error: pdfinfo pages for {pdf.name}")
    parts: list[str] = []
    for page in range(1, count + 1):
        proc = subprocess.run(
            [
                "pdftotext",
                "-layout",
                "-f",
                str(page),
                "-l",
                str(page),
                str(pdf),
                "-",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            raise SystemExit(f"error: pdftotext {pdf.name} page {page}: {proc.stderr[:200]}")
        parts.append(f"<!-- page: {page} -->")
        parts.append((proc.stdout or "").rstrip())
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def write_artifact(pdf: Path, markdown: str) -> Path:
    dest = artifact_path(pdf)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(markdown, encoding="utf-8")
    return dest


def mineru_reachable() -> bool:
    try:
        with urllib.request.urlopen(f"{MINERU_API}/health", timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def content_list_from_mineru(pdf: Path) -> list[dict] | None:
    boundary = "----claimprintexport"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="files"; filename="{pdf.name}"\r\n'.encode(),
            b"Content-Type: application/pdf\r\n\r\n",
            pdf.read_bytes(),
            b"\r\n",
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="backend"\r\n\r\n',
            b"pipeline\r\n",
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="return_content_list"\r\n\r\n',
            b"true\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    req = urllib.request.Request(
        f"{MINERU_API}/file_parse",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            task = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"skip: mineru-api {pdf.name} -> {exc}", file=sys.stderr)
        return None

    result_url = task.get("result_url")
    if not result_url:
        return None
    for _ in range(120):
        with urllib.request.urlopen(result_url, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("status") == "completed" and payload.get("results"):
            file_payload = payload["results"].get(pdf.stem) or next(iter(payload["results"].values()))
            raw = file_payload.get("content_list")
            if isinstance(raw, str):
                raw = json.loads(raw)
            if isinstance(raw, list):
                return [row for row in raw if isinstance(row, dict)]
            return None
        if payload.get("error"):
            print(f"skip: mineru-api {pdf.name} -> {payload['error']}", file=sys.stderr)
            return None
        time.sleep(2)
    print(f"skip: mineru-api {pdf.name} timed out", file=sys.stderr)
    return None


def write_content_for_pdf(
    pdf: Path,
    chunks: list[dict] | None,
    *,
    prefer_mineru: bool,
) -> Path | None:
    sidecar = None
    if prefer_mineru and mineru_reachable():
        blocks = content_list_from_mineru(pdf)
        if blocks:
            sidecar = spans_from_content_list(blocks, pdf_name=pdf.name)
    if sidecar is None and chunks:
        sidecar = spans_from_ragflow_chunks(chunks, pdf_name=pdf.name)
    if sidecar is None or not sidecar.spans:
        return None
    dest = write_content_sidecar(pdf, sidecar)
    return dest


def export_demo4(*, with_content: bool, content_only: bool, prefer_mineru: bool) -> int:
    load_env(ROOT / ".env")
    token = os.environ.get("RAGFLOW_API_KEY") or token_from_mysql()
    datasets = rows_of(api("GET", "/datasets?page_size=100", token), "datasets", "kbs")
    demo = next((ds for ds in datasets if (ds.get("name") or "") == "demo_4"), None)
    if demo is None:
        print("error: dataset demo_4 not found", file=sys.stderr)
        return 1
    ds_id = demo["id"]
    docs = rows_of(
        api("GET", f"/datasets/{ds_id}/documents?page_size=100", token),
        "docs",
        "documents",
    )
    by_name = {str(row.get("name") or ""): row for row in docs}
    written = 0
    for pdf in sorted(SAMPLES.glob("*.pdf")):
        row = by_name.get(pdf.name)
        if row is None:
            print(f"skip: {pdf.name} not in demo_4", file=sys.stderr)
            continue
        chunks = list_chunks(ds_id, row["id"], token)
        if not content_only:
            markdown = markdown_from_chunks(chunks)
            if not markdown.strip():
                print(f"skip: {pdf.name} has no chunks", file=sys.stderr)
                continue
            dest = write_artifact(pdf, markdown)
            print(f"wrote {dest.relative_to(ROOT)}")
        elif with_content:
            if not chunks:
                print(f"skip: {pdf.name} has no chunks", file=sys.stderr)
                continue
        if with_content:
            content_dest = write_content_for_pdf(pdf, chunks, prefer_mineru=prefer_mineru)
            if content_dest:
                print(f"wrote {content_dest.relative_to(ROOT)}")
            else:
                print(f"skip: {pdf.name} has no content spans", file=sys.stderr)
                continue
        written += 1
    if written == 0:
        return 1
    return 0


def export_bootstrap() -> int:
    written = 0
    for pdf in sorted(SAMPLES.glob("*.pdf")):
        dest = write_artifact(pdf, bootstrap_layout(pdf))
        print(f"wrote {dest.relative_to(ROOT)}")
        written += 1
    return 0 if written else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Export MinerU parse fixtures")
    parser.add_argument(
        "--bootstrap-layout",
        action="store_true",
        help="Write page-marked poppler text when demo_4 is not reachable",
    )
    parser.add_argument(
        "--with-content",
        action="store_true",
        help="Also write fixtures/mineru/<stem>.content.json span sidecars",
    )
    parser.add_argument(
        "--content-only",
        action="store_true",
        help="With --with-content, write only *.content.json (do not overwrite *.md)",
    )
    parser.add_argument(
        "--prefer-mineru-api",
        action="store_true",
        help="When --with-content, try mineru-api content_list before RAGFlow positions",
    )
    parser.add_argument(
        "--dataset",
        default="demo_4",
        help="RAGFlow dataset name (export path only)",
    )
    args = parser.parse_args()
    if args.dataset != "demo_4":
        print("error: only demo_4 is supported", file=sys.stderr)
        return 1
    if args.bootstrap_layout and (args.with_content or args.content_only):
        print("error: --with-content needs RAGFlow or mineru-api, not --bootstrap-layout", file=sys.stderr)
        return 1
    if args.content_only and not args.with_content:
        print("error: --content-only requires --with-content", file=sys.stderr)
        return 1
    FIXTURES.mkdir(parents=True, exist_ok=True)
    if args.bootstrap_layout:
        return export_bootstrap()
    return export_demo4(
        with_content=args.with_content,
        content_only=args.content_only,
        prefer_mineru=args.prefer_mineru_api,
    )


if __name__ == "__main__":
    raise SystemExit(main())
