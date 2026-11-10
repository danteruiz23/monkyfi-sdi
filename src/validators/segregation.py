"""Minimal customer scoping (D42). Deterministic: no model call.

If any document in the package (emails included) names a customer of the same tenant other than
the order's own customer, the package carries another customer's data: one critical finding
(SEG-OTHER-CUSTOMER) that blocks G1 (SPEC 8.3, D20). The check reads document text only to look
for names; it never takes a value from it. Full adversarial defense, including keeping the foreign
document's values out of the order, stays in Phase 7.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from ..ingest.documents import Document, squash
from .rules import finding_rules

SUFFIX = re.compile(r"\s*\(synthetic\)\s*$", re.I)


def load_register(path: Path) -> dict[str, list[str]]:
    """{tenant: [customer names]} from a customer register file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {t["tenant"]: list(t["customers"]) for t in data["tenants"]}


def core_name(name: str) -> str:
    """The name as it would be written in running text, without the synthetic suffix."""
    return SUFFIX.sub("", name).strip()


@lru_cache(maxsize=None)
def _pattern(name: str) -> re.Pattern:
    words = r"\s+".join(re.escape(w) for w in core_name(name).split())
    return re.compile(rf"(?<!\w){words}(?!\w)", re.I)


def other_customer_mentions(documents: list[Document], own_customer: str, customers: list[str]) -> list[dict]:
    """Every page that names a customer of the tenant other than `own_customer`."""
    own = core_name(own_customer).casefold()
    others = [c for c in customers if core_name(c).casefold() != own]
    hits = []
    for document in documents:
        for page in document.pages:
            text = squash(page.text)
            for name in others:
                if _pattern(name).search(text):
                    hits.append({"filename": document.filename, "doc_type": document.doc_type, "page": page.number,
                                 "location": "page text", "raw_value": name, "stale_source": False})
    return hits


def own_customer(extraction: dict) -> str | None:
    field = next((f for f in extraction["fields"] if f["field_key"] == "customer_name"), None)
    if field is None or field["status"] not in ("pending", "verified"):
        return None
    return field["raw_value"]


def scope_customers(extraction: dict, documents: list[Document], customers: list[str], findings: list[dict],
                    make_finding) -> list[dict]:
    """Adds the segregation finding, or merges the foreign mentions into one already raised on
    customer_name. Returns the findings list (new list; the input is not changed)."""
    config = finding_rules()["customer_scoping"]
    findings = [dict(f) for f in findings]
    existing = next((f for f in findings if f["rule_id"] == config["rule_id"]), None)
    customer = own_customer(extraction)
    if existing is None and customer is None:
        return findings  # customer missing or contradictory: already a finding of its own
    hits = other_customer_mentions(documents, customer or "", customers)
    if not hits:
        return findings
    if existing is not None:
        known = {(v["filename"], v["page"], v["raw_value"]) for v in existing["conflicting_values"]}
        existing["conflicting_values"] = existing["conflicting_values"] + [
            h for h in hits if (h["filename"], h["page"], h["raw_value"]) not in known]
        existing["evidence"] = dict(existing["evidence"], documents=sorted(
            set(existing["evidence"]["documents"]) | {h["filename"] for h in hits}))
        return findings
    field = next(f for f in extraction["fields"] if f["field_key"] == "customer_name")
    own_sources = [{"filename": s["filename"], "doc_type": s["doc_type"], "page": s["page"], "location": s["location"],
                    "raw_value": s["raw_value"], "stale_source": s["stale_source"]}
                   for s in field["sources"] if not s.get("placeholder")]
    documents_named = sorted({h["filename"] for h in hits})
    params = {"field": "customer_name", "version": extraction["version_no"], "count": 1 + len({h["raw_value"] for h in hits}),
              "documents": ", ".join(documents_named)}
    findings.append(make_finding(len(findings) + 1, config["rule_id"], config["action"], "customer_name",
                                 "identification", config["severity"], field["status"], own_sources + hits,
                                 [config["note_key"]], params))
    return findings
