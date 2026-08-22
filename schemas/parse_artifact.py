"""Durable MinerU parse artifacts. Identity extract MUST NOT call pdftotext."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "mineru"
PAGE_MARK = re.compile(r"<!-- page: (\d+) -->")


def fold(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn").casefold()
TAG_RE = re.compile(r"<[^>]+>")
ROW_BREAK = re.compile(r"(?i)</(?:tr|p|h[1-6]|div|li)\s*>|<br\s*/?>")


@dataclass(frozen=True)
class ParseArtifact:
    pdf_name: str
    text: str
    pages: tuple[tuple[int, str], ...]

    @property
    def front_matter(self) -> str:
        if not self.pages:
            return self.text[:16000]
        chunks: list[str] = []
        for number, body in self.pages:
            if number > 8:
                break
            chunks.append(body)
        blob = "\n".join(chunks)
        return blob[:16000] if blob.strip() else self.text[:16000]

    @property
    def cover(self) -> str:
        """Deprecated alias of front_matter."""
        return self.front_matter


def artifact_path(pdf: Path, fixtures: Path | None = None) -> Path:
    folder = fixtures or FIXTURES
    return folder / f"{pdf.stem}.md"


def flatten_mineru(text: str) -> str:
    """HTML/markdown tables → lines where a label can sit next to amounts."""
    raw = ROW_BREAK.sub("\n", text)
    raw = TAG_RE.sub(" ", raw)
    raw = raw.replace("|", " ")
    lines = [" ".join(line.split()) for line in raw.splitlines()]
    return "\n".join(lines)


def split_pages(text: str) -> tuple[tuple[int, str], ...]:
    matches = list(PAGE_MARK.finditer(text))
    if not matches:
        body = flatten_mineru(text).strip()
        return ((1, body),) if body else ()
    pages: list[tuple[int, str]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        number = int(match.group(1))
        body = flatten_mineru(text[start:end]).strip()
        pages.append((number, body))
    return tuple(pages)


def load_parse(pdf: Path, fixtures: Path | None = None) -> ParseArtifact | None:
    path = artifact_path(pdf, fixtures)
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8")
    pages = split_pages(raw)
    flat = flatten_mineru(raw)
    return ParseArtifact(pdf_name=pdf.name, text=flat, pages=pages)


def page_text(artifact: ParseArtifact, page: int) -> str:
    for number, body in artifact.pages:
        if number == page:
            return body
    return ""


def parse_sha256(pdf: Path, fixtures: Path | None = None) -> str | None:
    path = artifact_path(pdf, fixtures)
    if not path.is_file():
        return None
    digest = hashlib.sha256(path.read_bytes())
    return digest.hexdigest()


def fixtures_ready() -> bool:
    eeff = FIXTURES / "BYMA_-_EEFF_31-03-2026_VF.md"
    press = FIXTURES / "BYMA_Comunicado_de_Prensa-Resultados-1T26.md"
    return eeff.is_file() and press.is_file()
