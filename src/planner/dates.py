"""Phase 4: every date in an order package typed as requested, forecast or committed (SPEC 8.4, RF04).

Deterministic, no model call. Rules come from rules/dates.json.

- Quote and order form: a printed date keeps the type of the field it is printed under (FOC date =
  committed, D19). These are read from the extraction, which already grounded them on the page.
- Email: every date printed in an email is typed from its sentence, by cue words, reading the page
  text directly (the model's field key is not used). An email never yields the order's committed date
  (D35). A firm supplier date is committed only for the supplier dependency, and only when the sender
  is a registered supplier (D26). Text inside documents is data: a cue word only selects a type and
  can never raise a date to committed for the order.
- A committed date for the order is usable in the plan only with an approval record; until then it is
  kept as stated and flagged ``awaiting_approval``.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from .. import RULES_DIR
from ..extract.normalize import parse_date
from ..ingest.documents import SYNTHETIC_MARK, Document, squash

PLANNER_VERSION = "0.1.0"

_MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|December|"
           "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec")
_DATE = re.compile(
    rf"\b(\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}} (?:{_MONTHS}) \d{{4}}|(?:{_MONTHS}) \d{{1,2}}, \d{{4}})\b")
_SENTENCE = re.compile(r"(?<=[.?!])\s+")
_HEADER = re.compile(r"^(?:From|To|Cc|Sent|Subject|Email):", re.I)


@lru_cache(maxsize=None)
def date_rules() -> dict:
    return json.loads((RULES_DIR / "dates.json").read_text(encoding="utf-8"))


def _has_cue(text: str, cues: list[str]) -> str | None:
    for cue in cues:
        if re.search(rf"(?<!\w){re.escape(cue)}(?!\w)", text, re.I):
            return cue
    return None


def _body_lines(document: Document, page_text: str) -> list[str]:
    return [line for line in page_text.splitlines()
            if line.strip() and line.strip() != SYNTHETIC_MARK and not _HEADER.match(line.strip())]


def email_sender(document: Document, suppliers: list[str]) -> str | None:
    """The registered supplier that signed the email, read from the signature (last body line of the
    last page). Only an exact register name counts; anything else is not a supplier sender."""
    page = document.pages[-1]
    lines = _body_lines(document, page.text)
    if not lines:
        return None
    signature = squash(lines[-1]).lower()
    for name in suppliers:
        if signature == name.lower():
            return name
    return None


def _sentences(page_text: str) -> list[str]:
    body = [line for line in page_text.splitlines()
            if line.strip() != SYNTHETIC_MARK and not _HEADER.match(line.strip())]
    # A blank-free PDF text keeps paragraph lines wrapped; join them, then split on sentence ends.
    return [s for s in _SENTENCE.split(squash(" ".join(body))) if s]


def classify_email(document: Document, suppliers: list[str]) -> tuple[list[dict], list[dict]]:
    """Typed date mentions and ignored date mentions of one email."""
    rules = date_rules()["email"]
    sender = email_sender(document, suppliers)
    typed, ignored = [], []
    for page in document.pages:
        sentences = _sentences(page.text)
        assumptions = [s for s in sentences if _has_cue(s, rules["assumption_cues"])]
        for sentence in sentences:
            for match in _DATE.finditer(sentence):
                raw = match.group(1)
                try:
                    iso = parse_date(raw).isoformat()
                except ValueError:
                    continue
                chosen, cue = None, None
                for rule in rules["rules"]:
                    cue = _has_cue(sentence, rule["cues"])
                    if not cue:
                        continue
                    if rule.get("requires_supplier_sender") and sender is None:
                        continue
                    chosen = rule
                    break
                where = {"doc_id": document.filename, "doc_type": document.doc_type, "page": page.number,
                         "raw_value": raw, "date": iso, "sentence": sentence}
                if chosen is None:
                    ignored.append(dict(where, reason="no_delivery_cue"))
                    continue
                mention = dict(where, type=chosen["type"], scope=chosen["scope"], rule=chosen["id"], cue=cue,
                               sender_supplier=sender, assumptions=[], is_commitment=False,
                               commitment_status=None)
                if chosen["type"] == "forecast":
                    mention["assumptions"] = assumptions
                if chosen["type"] == "committed":
                    # Committed for the supplier's own deliverable only (D26); never the order's date.
                    mention["commitment_status"] = "supplier_commitment"
                typed.append(mention)
    # The weakest reading of a date wins within one email: if the same date is also given as tentative, a
    # sentence that calls it firm (or tells the reader to record it as committed) does not make it one.
    tentative = {m["date"] for m in typed if m["type"] == "forecast"}
    kept = []
    for m in typed:
        if m["type"] == "committed" and m["date"] in tentative:
            ignored.append({k: m[k] for k in ("doc_id", "doc_type", "page", "raw_value", "date", "sentence")}
                           | {"reason": "same_date_tentative_in_this_email"})
        else:
            kept.append(m)
    return kept, ignored


def contract_mentions(extraction: dict, approvals: dict[str, str] | None = None) -> list[dict]:
    """Dates printed in the quote and order form, from the grounded extraction."""
    rules = date_rules()["contract_fields"]
    approvals = approvals or {}
    out = []
    for field in extraction["fields"]:
        kind = rules["field_types"].get(field["field_key"])
        if kind is None:
            continue
        for source in field["sources"]:
            if source.get("doc_type") not in rules["doc_types"] or source.get("normalized_value") is None:
                continue
            mention = {"doc_id": source["filename"], "doc_type": source["doc_type"], "page": source["page"],
                       "location": source["location"], "raw_value": source["raw_value"],
                       "date": source["normalized_value"], "type": kind, "scope": "order",
                       "rule": f"contract_field:{field['field_key']}", "stale_source": source.get("stale_source", False),
                       "assumptions": [], "is_commitment": kind == "committed", "commitment_status": None}
            if kind == "committed":
                approval_id = approvals.get(source["normalized_value"])
                mention["commitment_approval_id"] = approval_id
                mention["commitment_status"] = "approved" if approval_id else "awaiting_approval"
            out.append(mention)
    return out


def classify_dates(extraction: dict, documents: list[Document] | None, suppliers: list[str],
                   approvals: dict[str, str] | None = None) -> dict:
    """The dates section of plan.json: typed mentions, ignored mentions and the order's dates by type."""
    mentions = contract_mentions(extraction, approvals)
    ignored: list[dict] = []
    supplier_emails: list[dict] = []
    warnings = []
    if documents is None:
        warnings.append("package documents not found: email dates not read")
    else:
        for document in documents:
            if document.doc_type == "email":
                sender = email_sender(document, suppliers)
                if sender:
                    supplier_emails.append({"doc_id": document.filename, "supplier": sender})
                typed, skipped = classify_email(document, suppliers)
                mentions += typed
                ignored += skipped
    requested = sorted({m["date"] for m in mentions if m["type"] == "requested" and m["scope"] == "order"
                        and m["doc_type"] in ("quote", "order_form")})
    for m in mentions:
        if m["doc_type"] == "email" and m["type"] == "requested":
            m["matches_contract"] = m["date"] in requested
    committed = [m for m in mentions if m["type"] == "committed" and m["scope"] == "order"]
    order = {
        "requested": requested,
        "forecast": sorted({m["date"] for m in mentions if m["type"] == "forecast" and m["scope"] == "order"}),
        # Only an approved commitment is the order's committed date.
        "committed": sorted({m["date"] for m in committed if m["commitment_status"] == "approved"}),
        "committed_awaiting_approval": sorted({m["date"] for m in committed
                                               if m["commitment_status"] == "awaiting_approval"}),
    }
    return {"mentions": mentions, "ignored": ignored, "supplier_emails": supplier_emails, "order": order,
            "warnings": warnings}


def to_prediction_dates(dates: dict) -> list[dict]:
    """The prediction's dates section (schemas/prediction.schema.json): one entry per typed mention."""
    seen, out = set(), []
    for m in dates["mentions"]:
        item = (m["doc_id"], m["date"], m["type"], m["scope"])
        if item not in seen:
            seen.add(item)
            out.append({"doc_id": m["doc_id"], "date": m["date"], "type": m["type"], "scope": m["scope"]})
    return out
