"""DOCX text from word/document.xml, without extra dependencies.

DOCX has no stored page numbers, so the whole document is page 1. Paragraphs are one line each;
a table row is one line per cell, in order, so a two-column "Field | Value" table reads like the
PDF tables do. Headers, footers, comments and tracked deletions are not read.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .documents import Page

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _paragraph_text(paragraph) -> str:
    parts = []
    for node in paragraph.iter():
        if node.tag == f"{W}t":
            parts.append(node.text or "")
        elif node.tag == f"{W}tab":
            parts.append("\t")
        elif node.tag in (f"{W}br", f"{W}cr"):
            parts.append("\n")
    return "".join(parts)


def _block_lines(body) -> list[str]:
    lines: list[str] = []
    for child in body:
        if child.tag == f"{W}p":
            lines.append(_paragraph_text(child))
        elif child.tag == f"{W}tbl":
            for row in child.iter(f"{W}tr"):
                for cell in row.findall(f"{W}tc"):
                    lines.append(" ".join(_paragraph_text(p) for p in cell.findall(f"{W}p")).strip())
    return lines


def read_docx_pages(path: Path) -> tuple[list[Page], list[str]]:
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ValueError(f"{path.name}: not a readable DOCX ({type(exc).__name__})") from exc
    root = ElementTree.fromstring(xml)
    body = root.find(f"{W}body")
    if body is None:
        return [Page(number=1, text="")], ["document has no body"]
    if root.find(f".//{W}del") is not None:
        warnings.append("tracked deletions present; deleted text was not read")
    text = "\n".join(line for line in _block_lines(body))
    warnings.append("DOCX has no page numbers; every location is on page 1")
    return [Page(number=1, text=text)], warnings
