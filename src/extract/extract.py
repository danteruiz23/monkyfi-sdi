"""Extract the critical fields of one order version: one model call per document, then grounding
and consolidation. Returns an extraction record (schemas/extraction.schema.json)."""

from __future__ import annotations

import re
from functools import lru_cache

from .. import PROMPTS_DIR
from ..ingest.documents import Document, now_utc
from ..providers import ModelRequest, Provider, generate_json
from .catalog import describe, extraction_rules, rules_version, union_rules
from .consolidate import consolidate, detect_product
from .ground import Mention, ground

EXTRACTOR_VERSION = "0.1.0"
_VERSION_TAG = re.compile(r"prompt_version:\s*([^\s·]+)")


@lru_cache(maxsize=None)
def _prompt(name: str) -> tuple[str, str]:
    text = (PROMPTS_DIR / name).read_text(encoding="utf-8")
    first, _, body = text.partition("\n")
    match = _VERSION_TAG.search(first)
    if not match:
        raise ValueError(f"prompts/{name} has no prompt_version tag on its first line")
    return match.group(1), body.strip()


def prompt_version() -> str:
    return ";".join(_prompt(n)[0] for n in ("system.md", "extract_fields.md"))


def _neutralize(text: str) -> str:
    """Document text cannot close the tags that frame it."""
    return re.sub(r"</?\s*(page|document)\b", lambda m: m.group(0).replace("<", "‹"), text, flags=re.I)


def render_document(document: Document) -> str:
    pages = "\n".join(f'<page number="{p.number}">\n{_neutralize(p.text)}\n</page>' for p in document.pages)
    return f'<document filename="{document.filename}">\n{pages}\n</document>'


def response_schema(keys: list[str]) -> dict:
    return {
        "type": "object", "additionalProperties": False, "required": ["mentions"],
        "properties": {"mentions": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["field_key", "raw_value", "page", "location"],
            "properties": {"field_key": {"enum": keys}, "raw_value": {"type": "string"},
                           "page": {"type": "integer", "minimum": 1}, "location": {"type": "string"}}}}},
    }


def build_request(document: Document) -> ModelRequest:
    catalog = union_rules()
    _, system = _prompt("system.md")
    _, task = _prompt("extract_fields.md")
    user = (task.replace("{catalog}", "\n".join(f"- {describe(r)}" for r in catalog.values()))
                .replace("{document}", render_document(document)))
    return ModelRequest(system=system, user=user, schema=response_schema(list(catalog)), schema_name="field_mentions")


def extract_version(documents: list[Document], provider: Provider, *, order_dir_id: str, version_no: int,
                    on_document=None) -> dict:
    keys = set(union_rules())
    mentions: list[Mention] = []
    calls, rejected_all, doc_records = [], [], []
    for document in documents:
        record = {"filename": document.filename, "sha256": document.sha256, "doc_type": document.doc_type,
                  "title": document.title, "format": document.format, "pages": len(document.pages),
                  "ingested_at": document.ingested_at, "has_synthetic_mark": document.has_synthetic_mark,
                  "warnings": list(document.warnings), "mentions_proposed": 0, "mentions_kept": 0}
        doc_records.append(record)
        if not any(p.text.strip() for p in document.pages):
            continue
        response = generate_json(provider, build_request(document))
        proposed = response.data["mentions"]
        kept, rejected = ground(document, proposed, keys)
        mentions += kept
        rejected_all += rejected
        record.update(mentions_proposed=len(proposed), mentions_kept=len(kept))
        calls.append({"filename": document.filename, "attempts": response.attempts, "latency_s": response.latency_s,
                      "usage": response.usage})
        if on_document:
            on_document(document, kept, rejected)

    product = detect_product(mentions)
    warnings = []
    if product is None:
        warnings.append("product could not be determined from the documents; no field statuses were set")
    fields = consolidate(mentions, product, current_version=version_no) if product else []
    package_ingested = min((d["ingested_at"] for d in doc_records), default=now_utc())
    for f in fields:
        f["ingested_at"] = next((d["ingested_at"] for d in doc_records if f["source"] and
                                 d["filename"] == f["source"]["filename"]), package_ingested)
        f["fact_timestamp"] = None  # the documents state no time for the facts they carry
    sources = set(extraction_rules()["field_source_doc_types"])
    return {
        "synthetic": True,
        "order_dir_id": order_dir_id, "version_no": version_no, "product": product,
        "run": {"provider": provider.name, "model": provider.model, "prompt_version": prompt_version(),
                "rules_version": rules_version(), "extractor_version": EXTRACTOR_VERSION, "extracted_at": now_utc()},
        "documents": doc_records,
        "fields": fields,
        "observations": [vars(m) for m in mentions if m.doc_type not in sources],
        "rejected_mentions": [vars(r) for r in rejected_all],
        "model_calls": calls,
        "warnings": warnings,
    }
