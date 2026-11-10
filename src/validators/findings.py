"""Findings from an extraction record. Deterministic: no model call (SPEC 7.1, RF02, RF03).

Every G1 field of the product that is missing or contradictory raises one finding with its rule,
severity, sources, owner, due date and action. Nothing else raises a finding, so a clean order has
none. The agent never lowers a severity; a human can, with a recorded reason (D20).
"""

from __future__ import annotations

import copy
from datetime import date, timedelta

from ..extract.catalog import ENDS, product_rules
from .rules import finding_rules, gate_rule, higher, severity_rank

DEFECTIVE = ("missing", "contradictory")


def add_business_days(start: date, days: int) -> date:
    current = start
    while days > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days -= 1
    return current


def parties(field_key: str, group: str) -> tuple[str, str]:
    """(internal owner, resolving party) of a finding on this field (D46)."""
    owners = finding_rules()["owners"]
    end, _, rest = field_key.partition(".")
    base_key = rest if end in ENDS else field_key
    entry = owners["by_field"].get(base_key) or owners["by_group"].get(group) or owners["default"]
    resolver = entry["resolving_party"]
    if resolver == "customer_technical_contact" and end in ENDS:
        resolver = f"{resolver}_{end}"
    return entry["internal_owner"], resolver


def _matches(when: dict, field: dict, rule: dict, by_key: dict[str, dict]) -> bool:
    if field["status"] not in when["status"]:
        return False
    if "field_key" in when and when["field_key"] != field["field_key"]:
        return False
    if "group" in when and when["group"] != rule["group"]:
        return False
    required = when.get("requires")
    if required:
        other = by_key.get(required["field_key"])
        if other is None or other["normalized_value"] != required["normalized_value"]:
            return False
    return True


def _conflicting_values(field: dict) -> list[dict]:
    return [{"filename": s["filename"], "doc_type": s["doc_type"], "page": s["page"], "location": s["location"],
             "raw_value": s["raw_value"], "stale_source": s["stale_source"]}
            for s in field["sources"] if not s.get("placeholder")]


def _only_stale_sources_disagree(field: dict) -> bool:
    """True when the documents of the current version agree and only earlier-version documents differ."""
    current = {repr(s["normalized_value"]) for s in field["sources"] if not s["stale_source"] and not s.get("placeholder")}
    stale = [s for s in field["sources"] if s["stale_source"]]
    return bool(stale) and len(current) <= 1


def _finding(number: int, rule_id: str, action: str, field_key: str, group: str, severity: str, status: str,
             conflicting: list[dict], notes: list[str], params: dict, as_of: date) -> dict:
    config = finding_rules()
    blocks = severity in gate_rule("G1")["blocking_severities"]
    owner, resolver = parties(field_key, group)
    return {
        "finding_id": f"F{number}", "rule_id": rule_id, "field_key": field_key, "gate": "G1",
        "severity": severity, "field_status": status,
        "conflicting_values": conflicting,
        "evidence": {"notes": notes, "documents": sorted({v["filename"] for v in conflicting})},
        "impact": "confirmed" if blocks else "possible",
        "blocks_gate": blocks,
        "owner": owner, "resolving_party": resolver,
        # A missing or contradictory value is never settled by the agent: the resolving party validates it (SPEC 8).
        "escalated": True, "escalated_to": resolver,
        "due_date": add_business_days(as_of, config["due_in_business_days"][severity]).isoformat(),
        "action": {"key": f"finding_action.{action}", "params": params},
        "description": {"key": f"finding_rule.{rule_id}", "params": params},
        "status": "open",
    }


def validate(extraction: dict, as_of: date, documents=None, customers: list[str] | None = None,
             suppliers: list[str] | None = None) -> list[dict]:
    """Findings for one order version, in rules-file order. With the package's documents and the
    tenant's customer register, the customer-scoping check runs too (D42); with the documents, the
    customer date change check runs too (D57)."""
    findings = _field_findings(extraction, as_of)

    def make(number, rule_id, action, field_key, group, severity, status, conflicting, notes, params):
        return _finding(number, rule_id, action, field_key, group, severity, status, conflicting, notes, params,
                        as_of)
    if documents is not None and customers is not None:
        from .segregation import scope_customers
        findings = scope_customers(extraction, documents, customers, findings, make)
    if documents is not None:
        from .date_change import customer_date_changes
        findings = customer_date_changes(extraction, documents, suppliers or [], findings, make)
    return findings


def _field_findings(extraction: dict, as_of: date) -> list[dict]:
    config = finding_rules()
    if extraction["product"] is None:
        u = config["product_undetermined"]
        return [_finding(1, u["rule_id"], u["action"], u["field_key"], "identification", u["severity"], "missing", [],
                         list(extraction["warnings"]), {"field": u["field_key"]}, as_of)]

    catalog = product_rules(extraction["product"])
    by_key = {f["field_key"]: f for f in extraction["fields"]}
    version = extraction["version_no"]
    findings = []
    for field in extraction["fields"]:
        rule = catalog[field["field_key"]]
        if rule["gate"] != "G1" or field["status"] not in DEFECTIVE:
            continue
        matched = next(r for r in config["finding_rules"] if _matches(r["when"], field, rule, by_key))
        severity = higher(rule["missing_severity"], matched.get("min_severity"))
        conflicting = _conflicting_values(field) if field["status"] == "contradictory" else []
        stale_documents = sorted({v["filename"] for v in conflicting if v["stale_source"]})
        action = matched["action"]
        if field["status"] == "contradictory" and _only_stale_sources_disagree(field):
            action = config["stale_source_action"]
        params = {"field": field["field_key"], "version": version,
                  "count": len({repr(s["normalized_value"]) for s in field["sources"] if not s.get("placeholder")}),
                  "documents": ", ".join(stale_documents or sorted({v["filename"] for v in conflicting}))}
        findings.append(_finding(len(findings) + 1, matched["rule_id"], action, field["field_key"], rule["group"],
                                 severity, field["status"], conflicting, list(field["notes"]), params, as_of))
    return findings


def lower_severity(finding: dict, severity: str, approver: str, reason: str, decided_at: str) -> dict:
    """Only a human lowers a severity, with a recorded reason (D20). The original severity is kept."""
    if not approver or not approver.strip() or not reason or not reason.strip():
        raise ValueError("lowering a severity needs a named approver and a reason")
    rank = severity_rank()
    if rank[severity] >= rank[finding["severity"]]:
        raise ValueError("lower_severity only lowers; a higher severity needs no approval")
    out = copy.deepcopy(finding)
    out.setdefault("original_severity", finding["severity"])
    out["severity"] = severity
    out["blocks_gate"] = severity in gate_rule(finding["gate"])["blocking_severities"]
    out["severity_change"] = {"approver": approver.strip(), "reason": reason.strip(), "decided_at": decided_at}
    return out
