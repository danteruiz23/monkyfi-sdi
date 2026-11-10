"""Grounding: a mention is kept only if its text is printed in the document (SPEC 8: no value without a source).

The check is literal after collapsing whitespace, so a value wrapped across lines still matches.
A mention whose text is on a different page of the same document is kept with the page corrected
and a note. Anything else is rejected and reported, never silently dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..ingest.documents import Document, squash


@dataclass
class Mention:
    field_key: str
    raw_value: str
    page: int
    location: str
    filename: str
    doc_type: str
    notes: list[str] = field(default_factory=list)


@dataclass
class Rejected:
    field_key: str
    raw_value: str
    page: int | None
    filename: str
    reason: str


def ground(document: Document, proposed: list[dict], known_keys: set[str]) -> tuple[list[Mention], list[Rejected]]:
    kept: list[Mention] = []
    rejected: list[Rejected] = []
    pages = {p.number: squash(p.text) for p in document.pages}
    seen: set[tuple[str, str, int, str]] = set()
    for item in proposed:
        key, raw, page = item["field_key"], squash(item["raw_value"]), item["page"]
        location = squash(item.get("location") or "")
        if key not in known_keys:
            rejected.append(Rejected(key, raw, page, document.filename, "field key is not in the catalog"))
            continue
        if not raw:
            rejected.append(Rejected(key, raw, page, document.filename, "empty value"))
            continue
        notes = []
        if raw not in pages.get(page, ""):
            elsewhere = [n for n, text in pages.items() if raw in text]
            if not elsewhere:
                rejected.append(Rejected(key, raw, page, document.filename,
                                         "text is not printed in the document (not grounded)"))
                continue
            notes.append(f"model cited page {page}; text found on page {elsewhere[0]}")
            page = elsewhere[0]
        signature = (key, raw, page, location)
        if signature in seen:
            continue
        seen.add(signature)
        kept.append(Mention(key, raw, page, location, document.filename, document.doc_type, notes))
    return kept, rejected
