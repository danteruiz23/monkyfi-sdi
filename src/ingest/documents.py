"""Documents of an order package, read page by page.

A Document keeps the file name, a SHA-256 of the bytes, its type, its pages and when it was
ingested. Pages are numbered from 1. DOCX files have no reliable page numbers, so a DOCX is read
as a single page and locations point at paragraph and table positions instead.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .. import RULES_DIR

SUPPORTED = (".pdf", ".docx")
_EXTRACTION_RULES = json.loads((RULES_DIR / "extraction.json").read_text(encoding="utf-8"))
SYNTHETIC_MARK = "SYNTHETIC — NOT REAL DATA"


@dataclass(frozen=True)
class Page:
    number: int
    text: str


@dataclass
class Document:
    filename: str
    sha256: str
    doc_type: str
    title: str
    pages: list[Page]
    ingested_at: str
    format: str
    warnings: list[str] = field(default_factory=list)

    @property
    def has_synthetic_mark(self) -> bool:
        return any(SYNTHETIC_MARK in p.text for p in self.pages)

    def page(self, number: int) -> Page | None:
        return next((p for p in self.pages if p.number == number), None)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def title_of(pages: list[Page]) -> str:
    """First non-empty line that is not the synthetic mark."""
    for page in pages:
        for line in page.text.splitlines():
            line = line.strip()
            if line and SYNTHETIC_MARK not in line:
                return line
    return ""


def classify(title: str) -> str:
    """Document type from its title (rules/extraction.json). Deterministic; no match is 'other'."""
    lowered = title.lower()
    for entry in _EXTRACTION_RULES["doc_types"]:
        if any(pattern in lowered for pattern in entry["title_patterns"]):
            return entry["doc_type"]
    return "other"


def read_document(path: Path, ingested_at: str | None = None) -> Document:
    data = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from .pdf import read_pdf_pages
        pages, warnings = read_pdf_pages(path)
    elif suffix == ".docx":
        from .docx import read_docx_pages
        pages, warnings = read_docx_pages(path)
    else:
        raise ValueError(f"unsupported document format: {path.name} (supported: {', '.join(SUPPORTED)})")
    title = title_of(pages)
    if not any(p.text.strip() for p in pages):
        warnings.append("no extractable text (a scanned document needs OCR, which is not built)")
    return Document(filename=path.name, sha256=hashlib.sha256(data).hexdigest(), doc_type=classify(title),
                    title=title, pages=pages, ingested_at=ingested_at or now_utc(), format=suffix[1:],
                    warnings=warnings)


def read_package(directory: Path, ingested_at: str | None = None) -> list[Document]:
    """Every supported document in a directory, in file-name order."""
    paths = sorted(p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED)
    if not paths:
        raise FileNotFoundError(f"no PDF or DOCX documents in {directory}")
    stamp = ingested_at or now_utc()
    return [read_document(p, stamp) for p in paths]


_SPACE = re.compile(r"\s+")


def squash(text: str) -> str:
    """Collapse every run of whitespace (including line breaks) to one space."""
    return _SPACE.sub(" ", text).strip()
