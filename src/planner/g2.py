"""Gate G2, ready for execution (SPEC 6, D54, D65). Requirements in rules/gates.json.

Deterministic. The agent recommends pass or block from the plan and from gate records; a human decides.
Records (approvals, assignments, confirmations, evidence) are seeded in data/synthetic/gate_records.json and
are never created, edited or inferred by the agent. Every applicable requirement blocks.
"""

from __future__ import annotations

from ..validators.rules import gate_rule

ENDS = ("a_end", "z_end")


def _value(extraction: dict, key: str):
    field = next((f for f in extraction["fields"] if f["field_key"] == key), None)
    if field is None or field["status"] not in ("pending", "verified"):
        return None
    return field["normalized_value"]


def _records(records: list[dict], kind: str, **match) -> list[dict]:
    return [r for r in records if r["kind"] == kind and all(r.get(k) == v for k, v in match.items())]


def order_records(all_records: list[dict], order_id: str, version_no: int) -> list[dict]:
    return [r for r in all_records if r["order_id"] == order_id and r["version_no"] == version_no]


def apply_access_type(plan: dict, records: list[dict]) -> None:
    """An access_type record (Engineering) settles an 'unknown' on-net/off-net milestone and resolves its action."""
    [record] = _records(records, "access_type")[-1:] or [None]
    if record is None:
        return
    for m in plan["milestones"]:
        if m["key"] in ("third_party_access", "supplier_segments_foc") and m["applicability"] == "unknown":
            m["applicability"] = "not_applicable" if record["value"] == "on_net" else "applies"
            m["applicability_reason"] = f"access_{record['value']}_confirmed"
            for action in plan["actions"]:
                if action["action_id"] in m["actions"] and action["status"] == "open":
                    action.update(status="resolved", resolved_by=record["record_id"])


def _result(rule: dict, missing: list[str], evidence: list[str], applies: bool = True) -> dict:
    return {"id": rule["id"], "owner": rule["owner"],
            "result": "not_applicable" if not applies else "unmet" if missing else "met",
            "missing": missing if applies else [], "evidence": evidence}


def evaluate_g2(product: str | None, extraction: dict, validation: dict | None, plan: dict,
                records: list[dict], evaluated_at: str) -> dict:
    rules = gate_rule("G2")["requirements"]
    out = []
    for rule in rules:
        if product not in rule["products"]:
            continue
        rid, missing, evidence, applies = rule["id"], [], [], True
        if rid == "g1_passed":
            gate = validation["gate"] if validation else None
            decision = gate and gate.get("human_decision")
            if not decision or decision["outcome"] != "pass":
                missing.append("g1_human_pass")
            else:
                evidence.append(decision["approval"].get("record_id") or "g1_decision")
            open_critical = [f["finding_id"] for f in (validation or {}).get("findings", [])
                             if f["severity"] == "critical" and f["status"] in ("open", "in_progress")]
            missing += [f"open_critical_finding:{f}" for f in open_critical]
        elif rid == "design_approved":
            found = [r for r in _records(records, "design_approval", decision="approved")
                     if r.get("role") == "engineering" and r.get("recorded_by")]
            missing += [] if found else ["design_approval"]
            evidence += [r["record_id"] for r in found]
        elif rid == "ports_assigned":
            for end in ENDS:
                found = _records(records, "port_assignment", end=end)
                missing += [] if found else [f"port_assignment:{end}"]
                evidence += [r["record_id"] for r in found]
        elif rid == "optical_path_assigned":
            found = _records(records, "optical_path_assignment")
            missing += [] if found else ["optical_path_assignment"]
            evidence += [r["record_id"] for r in found]
            for end in ENDS:
                found = _records(records, "port_or_transponder_assignment", end=end)
                missing += [] if found else [f"port_or_transponder_assignment:{end}"]
                evidence += [r["record_id"] for r in found]
        elif rid == "cross_connects":
            needed = [end for end in ENDS if _value(extraction, f"{end}.cross_connect.required") is True]
            unknown = [end for end in ENDS if _value(extraction, f"{end}.cross_connect.required") is None]
            missing += [f"cross_connect_required_not_stated:{end}" for end in unknown]
            for end in needed:
                if not _value(extraction, f"{end}.cross_connect.loa_cfa_reference"):
                    missing.append(f"loa_cfa_reference:{end}")
                found = _records(records, "cross_connect_request", end=end)
                missing += [] if found else [f"cross_connect_request:{end}"]
                evidence += [r["record_id"] for r in found]
            for shared in plan.get("shared_resources", []):
                if shared["kind"] == "cross_connect" and shared["is_blocked"]:
                    missing.append(f"shared_resource_blocked:{shared['shared_resource_id']}")
        elif rid == "third_party_segments":
            supplier = next((m for m in plan["milestones"]
                             if m["key"] in ("third_party_access", "supplier_segments_foc")), None)
            if supplier and supplier["applicability"] == "unknown":
                missing.append("access_type_unknown")
            for d in plan.get("dependencies", []):
                if d["supplier_date_type"] != "committed":
                    missing.append(f"supplier_firm_foc:{d['dependency_id']}:"
                                   f"{'no_date' if d['supplier_date'] is None else 'forecast_only'}")
            evidence += [r["record_id"] for r in _records(records, "access_type")]
        elif rid == "site_access":
            for end in ENDS:
                for kind in ("site_access_confirmation", "access_contacts_confirmation"):
                    found = [r for r in _records(records, kind, end=end) if r.get("role") == "sdm"]
                    missing += [] if found else [f"{kind}:{end}"]
                    evidence += [r["record_id"] for r in found]
        elif rid == "route_diversity":
            required = _value(extraction, "route_diversity.required")
            applies = required is not False
            if required is None:
                missing.append("route_diversity_required_not_stated")
            elif required:
                if not _value(extraction, "route_diversity.reference_circuit_ids"):
                    missing.append("reference_circuit_ids")
                found = [r for r in _records(records, "diversity_evidence", decision="accepted")
                         if r.get("role") == "engineering"]
                missing += [] if found else ["diversity_evidence"]
                evidence += [r["record_id"] for r in found]
        elif rid == "protection_design":
            protection = _value(extraction, "protection.type")
            applies = protection != "unprotected"
            if protection is None:
                missing.append("protection_type_not_stated")
            elif applies:
                found = [r for r in _records(records, "protection_design_approval", decision="approved")
                         if r.get("role") == "engineering"]
                missing += [] if found else ["protection_design_approval"]
                evidence += [r["record_id"] for r in found]
        out.append(_result(rule, missing, evidence, applies))
    recommendation = "block" if any(r["result"] == "unmet" for r in out) or not out else "pass"
    human, warnings = None, []
    for record in _records(records, "gate_decision", gate="G2"):
        if record["decision"] == "approved" and recommendation == "pass" and record.get("recorded_by"):
            human = {"decision": "approved", "outcome": "pass",
                     "approval": {"entity": "gate_evaluation", "decision": "approved", "approver": record["recorded_by"],
                                  "reason": record.get("reason"), "created_at": record["recorded_at"],
                                  "record_id": record["record_id"]}}
        else:
            warnings.append(f"gate record {record['record_id']} not applied: G2 recommends {recommendation}")
    return {"gate": "G2", "recommendation": recommendation, "requirements": out,
            "unmet_requirements": [r["id"] for r in out if r["result"] == "unmet"],
            "human_decision": human, "evaluated_at": evaluated_at, "warnings": warnings}


def g2_milestone_state(plan: dict, g2: dict) -> None:
    """D65: the G2 result is shown as the state of the G2 milestone."""
    for m in plan["milestones"]:
        if m["key"] != "g2":
            continue
        if g2["human_decision"]:
            m["state"], m["blocked_by"] = "completed", []
        elif g2["recommendation"] == "pass":
            m["state"], m["blocked_by"] = "awaiting_decision", []
        else:
            m["state"], m["blocked_by"] = "blocked", list(g2["unmet_requirements"])
