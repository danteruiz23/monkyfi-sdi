"""PDF text, one entry per page, with pypdf. No OCR: a page without a text layer comes back empty."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from .documents import Page


def read_pdf_pages(path: Path) -> tuple[list[Page], list[str]]:
    reader = PdfReader(path)
    warnings: list[str] = []
    if reader.is_encrypted:
        raise ValueError(f"{path.name}: encrypted PDF; it needs a password, which is never handled automatically")
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # pypdf raises several types on damaged pages
            warnings.append(f"page {number}: text could not be read ({type(exc).__name__})")
            text = ""
        pages.append(Page(number=number, text=text))
    return pages, warnings
