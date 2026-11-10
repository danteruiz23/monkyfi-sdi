"""Gate G1 (SPEC 6, D28, rules/gates.json). The agent recommends pass or block; a human decides.

G1 is blocked by any open finding whose severity is a blocking severity. `verified` is never
required. An override is a human decision recorded next to the recommendation: it needs a reason
and an approver, and it changes neither the recommendation nor the findings behind it.
"""

from __future__ import annotations

import copy

from .rules import gate_rule


def evaluate_g1(findings: list[dict], evaluated_at: str) -> dict:
    rule = gate_rule("G1")
    blocking = [f for f in findings if f["gate"] == "G1" and f["status"] in ("open", "in_progress")
                and f["severity"] in rule["blocking_severities"]]
    return {
        "gate": "G1",
        "recommendation": "block" if blocking else "pass",
        "unmet_requirements": [{"finding_id": f["finding_id"], "rule_id": f["rule_id"], "field_key": f["field_key"],
                                "severity": f["severity"]} for f in blocking],
        "non_blocking_finding_ids": [f["finding_id"] for f in findings if f not in blocking],
        "evaluated_at": evaluated_at,
        "human_decision": None,
    }


def override_gate(validation: dict, approver: str, reason: str, decided_at: str) -> dict:
    """A human lets a blocked order through G1. Returns a new validation record with the decision and an
    approval row; the recommendation, the unmet requirements and every finding are kept."""
    if not approver or not approver.strip():
        raise ValueError("an override needs a named approver")
    if not reason or not reason.strip():
        raise ValueError("an override needs a reason")
    gate = validation["gate"]
    if gate["recommendation"] != "block":
        raise ValueError("only a block recommendation can be overridden")
    if gate["human_decision"] is not None:
        raise ValueError("this gate evaluation already has a human decision")
    out = copy.deepcopy(validation)
    approval = {"entity": "gate_evaluation", "decision": "override", "approver": approver.strip(),
                "reason": reason.strip(), "created_at": decided_at}
    out["gate"]["human_decision"] = {"decision": "override", "outcome": "pass", "approval": approval}
    blocking = {u["finding_id"] for u in gate["unmet_requirements"]}
    for finding in out["findings"]:
        if finding["finding_id"] in blocking:
            finding["status"] = "overridden"
    out["approvals"] = out.get("approvals", []) + [approval]
    return out


def record_decision(validation: dict, record: dict) -> dict:
    """A human decision on G1 taken from a gate record (D65: seeded, never created by the agent).
    'approved' confirms a pass recommendation. A blocked order needs an override with a reason
    (override_gate); an 'approved' record on a block recommendation is not applied."""
    if record.get("gate") != "G1" or record.get("decision") != "approved":
        raise ValueError("only an approved G1 record can be applied here")
    if not record.get("recorded_by", "").strip() or not record.get("reason", "").strip():
        raise ValueError("a gate decision needs a named approver and a reason")
    gate = validation["gate"]
    if gate["recommendation"] != "pass":
        raise ValueError("an approval cannot pass a blocked G1; it needs an override with a reason")
    if gate["human_decision"] is not None:
        raise ValueError("this gate evaluation already has a human decision")
    out = copy.deepcopy(validation)
    approval = {"entity": "gate_evaluation", "decision": "approved", "approver": record["recorded_by"].strip(),
                "reason": record["reason"].strip(), "created_at": record["recorded_at"],
                "record_id": record["record_id"]}
    out["gate"]["human_decision"] = {"decision": "approved", "outcome": "pass", "approval": approval}
    out["approvals"] = out.get("approvals", []) + [approval]
    return out
