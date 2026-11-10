"""Customer date change (D57): a requested date in an email that differs from the signed order form.

The email is evidence of a change request only. The order form value is not touched; a finding asks the
customer to confirm, and a change needs a new order version. Deterministic: email dates are typed by
src/planner/dates.py (rules/dates.json).
"""

from __future__ import annotations

from ..ingest.documents import Document
from ..planner.dates import classify_email
from .rules import finding_rules


def contract_requested(extraction: dict) -> tuple[dict | None, list[str]]:
    field = next((f for f in extraction["fields"] if f["field_key"] == "dates.requested"), None)
    if field is None:
        return None, []
    dates = sorted({s["normalized_value"] for s in field["sources"]
                    if s.get("doc_type") == "order_form" and s.get("normalized_value") and not s.get("stale_source")})
    return field, dates


def customer_date_changes(extraction: dict, documents: list[Document], suppliers: list[str], findings: list[dict],
                          make_finding) -> list[dict]:
    """Adds one DATE-CUSTOMER-CHANGE finding when an email's requested date differs from the order form.
    Returns a new findings list."""
    config = finding_rules()["customer_date_change"]
    findings = [dict(f) for f in findings]
    field, contract = contract_requested(extraction)
    if field is None or not contract:
        return findings  # no signed requested date to compare with: a field finding of its own, if any
    asked = []
    for document in documents:
        if document.doc_type != "email":
            continue
        typed, _ = classify_email(document, suppliers)
        asked += [m for m in typed if m["type"] == "requested" and m["date"] not in contract]
    if not asked:
        return findings
    own = [{"filename": s["filename"], "doc_type": s["doc_type"], "page": s["page"], "location": s["location"],
            "raw_value": s["raw_value"], "stale_source": s["stale_source"]}
           for s in field["sources"] if s.get("doc_type") == "order_form" and not s.get("placeholder")]
    hits = [{"filename": m["doc_id"], "doc_type": "email", "page": m["page"], "location": "page text",
             "raw_value": m["raw_value"], "stale_source": False} for m in asked]
    params = {"field": config["field_key"], "version": extraction["version_no"],
              "count": 1 + len({m["date"] for m in asked}), "documents": ", ".join(sorted({m["doc_id"] for m in asked}))}
    findings.append(make_finding(len(findings) + 1, config["rule_id"], config["action"], config["field_key"],
                                 config["group"], config["severity"], field["status"], own + hits,
                                 [config["note_key"]], params))
    return findings
