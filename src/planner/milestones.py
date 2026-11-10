"""Phase 4: milestone plan per product (UC04, RF04), from rules/milestones.json (D56).

Deterministic, no model call. Every milestone has an owner. Dates come only from typed date mentions
(src/planner/dates.py): nothing is estimated from durations, so a milestone without dated evidence is
``not_estimable``. A conditional milestone is never dropped silently: if the package does not say whether
it applies, its applicability is ``unknown``.
"""

from __future__ import annotations

import json
from functools import lru_cache

from .. import RULES_DIR


@lru_cache(maxsize=None)
def milestone_rules() -> dict:
    return json.loads((RULES_DIR / "milestones.json").read_text(encoding="utf-8"))


def _field(extraction: dict, key: str) -> dict | None:
    return next((f for f in extraction["fields"] if f["field_key"] == key), None)


def _cross_connect_any_end(extraction: dict) -> tuple[str, str]:
    values = []
    for end in ("a_end", "z_end"):
        field = _field(extraction, f"{end}.cross_connect.required")
        ok = field is not None and field["status"] in ("pending", "verified")
        values.append(field["normalized_value"] if ok else None)
    if any(v is True for v in values):
        return "applies", "cross_connect_required"
    if all(v is False for v in values):
        return "not_applicable", "no_cross_connect"
    return "unknown", "cross_connect_not_stated"


def _supplier_involved(dates: dict) -> tuple[str, str]:
    if any(m.get("sender_supplier") for m in dates["mentions"]) or dates.get("supplier_emails"):
        return "applies", "supplier_email_in_package"
    return "unknown", "no_supplier_evidence"


def _single(candidates: list[dict]) -> tuple[dict | None, str | None]:
    """One dated piece of evidence, or none. Two different dates are never reconciled by the agent."""
    distinct = {m["date"] for m in candidates}
    if not distinct:
        return None, "no_dated_evidence"
    if len(distinct) > 1:
        return None, "conflicting_dates"
    return candidates[0], None


def _evidence(m: dict) -> dict:
    return {"doc_id": m["doc_id"], "page": m["page"], "raw_value": m["raw_value"], "type": m["type"],
            "scope": m["scope"], "sentence": m.get("sentence"), "location": m.get("location")}


def build_milestones(product: str | None, extraction: dict, dates: dict, validation: dict | None) -> dict:
    if product not in milestone_rules()["products"]:
        return {"milestones": [], "actions": [], "warnings": ["product undetermined: no milestone template"]}
    mentions = dates["mentions"]
    supplier_dates = [m for m in mentions if m.get("sender_supplier") and m["type"] in ("forecast", "committed")]
    other_forecasts = [m for m in mentions if m["type"] == "forecast" and m["scope"] == "order"
                       and not m.get("sender_supplier")]
    order = dates["order"]
    gate = validation["gate"] if validation else None
    out, warnings, actions = [], [], []
    unknown_actions = milestone_rules()["unknown_actions"]
    for rule in milestone_rules()["products"][product]:
        applicability, reason = "applies", None
        if rule.get("condition") == "cross_connect_any_end":
            applicability, reason = _cross_connect_any_end(extraction)
        elif rule.get("condition") == "supplier_involved":
            applicability, reason = _supplier_involved(dates)
        m = {"key": rule["key"], "owner": rule["owner"], "is_critical": rule["is_critical"],
             "predecessors": rule["predecessors"], "applicability": applicability,
             "applicability_reason": reason, "state": "not_started", "blocked_by": [],
             "requested_date": None, "forecast_date": None, "forecast_assumptions": [],
             "forecast_status": "not_estimable", "forecast_reason": "no_dated_evidence", "forecast_evidence": None,
             "committed_date": None, "commitment_approval_id": None, "committed_awaiting_approval": None,
             "requested_conflict": []}
        if rule.get("gate") == "G1":
            if gate is None:
                m["state"] = "not_evaluated"
            elif gate.get("human_decision") and gate["human_decision"]["outcome"] == "pass":
                m["state"] = "completed"
            elif gate["recommendation"] == "block":
                m["state"] = "blocked"
                m["blocked_by"] = [u["finding_id"] for u in gate["unmet_requirements"]]
            else:
                m["state"] = "awaiting_decision"
        elif rule.get("gate"):
            m["state"] = "not_evaluated"  # G2 is evaluated in Phase 4 step 6
        if rule.get("supplier_milestone") and applicability != "not_applicable":
            chosen, why = _single(supplier_dates)
            if chosen:
                m.update(forecast_date=chosen["date"], forecast_status="estimated", forecast_reason=None,
                         forecast_evidence=_evidence(chosen),
                         forecast_assumptions=list(chosen.get("assumptions") or []))
                if chosen["type"] == "committed":
                    # A supplier's FOC supports a forecast; it is not the carrier's commitment (D26).
                    m["forecast_assumptions"].append(
                        f"supplier firm commitment for its own deliverable ({chosen['doc_id']} p.{chosen['page']})")
            else:
                m["forecast_reason"] = why
        if rule.get("delivery_milestone"):
            # The signed order form is the authoritative source of the requested date (rules/fields.common.json).
            # If the quote disagrees, the order form date is used and the disagreement stays visible; the
            # validators already raised a finding on dates.requested.
            signed = sorted({x["date"] for x in mentions if x["type"] == "requested" and x["doc_type"] == "order_form"
                             and not x.get("stale_source")})
            m["requested_date"] = signed[0] if len(signed) == 1 else None
            m["requested_conflict"] = sorted(set(order["requested"]) - set(signed)) if signed else order["requested"]
            if len(signed) > 1:
                warnings.append("more than one requested date in the signed order form: none used")
            chosen, why = _single(other_forecasts)
            if chosen:
                m.update(forecast_date=chosen["date"], forecast_status="estimated", forecast_reason=None,
                         forecast_evidence=_evidence(chosen),
                         forecast_assumptions=list(chosen.get("assumptions") or []))
            else:
                m["forecast_reason"] = why
            committed = [x for x in mentions if x["type"] == "committed" and x["scope"] == "order"]
            approved = [x for x in committed if x.get("commitment_status") == "approved"]
            if approved:
                m["committed_date"] = approved[0]["date"]
                m["commitment_approval_id"] = approved[0]["commitment_approval_id"]
            awaiting = sorted({x["date"] for x in committed if x.get("commitment_status") == "awaiting_approval"})
            m["committed_awaiting_approval"] = awaiting[0] if len(awaiting) == 1 else None
        if m["forecast_date"] and not m["forecast_assumptions"]:
            warnings.append(f"{m['key']}: forecast without stated assumptions")
        if applicability == "unknown" and rule.get("condition") in unknown_actions:
            config = unknown_actions[rule["condition"]]
            actions.append({"action_id": f"A{len(actions) + 1}", "action": config["action"], "milestone": rule["key"],
                            "owner": config["owner"], "reason": reason, "status": "open", "due_date": None,
                            "decision": "D60"})
            m["actions"] = [actions[-1]["action_id"]]
        else:
            m["actions"] = []
        out.append(m)
    return {"milestones": out, "actions": actions, "warnings": warnings}
