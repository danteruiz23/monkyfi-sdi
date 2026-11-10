"""Gate G2 (D54, D65) and seeded human gate decisions."""

from __future__ import annotations

import copy

import pytest

from conftest import DATA, GOLDENS, load

from test_planner_dependencies import AS_OF, REGISTER
from test_planner_dates import PACKAGES, golden_extraction
from test_planner_shared import CURRENT, RECORDS, run_dataset  # noqa: F401  (dataset linked as one run)

from src.planner import cli
from src.planner.g2 import apply_access_type, evaluate_g2, g2_milestone_state, order_records
from src.planner.shared import attach_to_plan
from src.validators.gate import evaluate_g1, record_decision
from src.validators.rules import gate_rule

SEEDED = load(DATA / "gate_records.json")
ALL = SEEDED["records"]


def extraction_of(order):
    golden = GOLDENS[CURRENT[order]]
    extraction = golden_extraction(golden)
    expected = {f["field_key"]: f for f in golden["expected_fields"]}
    for field in extraction["fields"]:
        field["status"] = expected[field["field_key"]]["expected_status"]
        field["normalized_value"] = expected[field["field_key"]]["normalized_value"]
    return extraction


def validation_of(order, records):
    golden = GOLDENS[CURRENT[order]]
    findings = [{"finding_id": f["finding_id"], "rule_id": f["rule_id"], "field_key": f["field_key"], "gate": "G1",
                 "severity": f["severity"], "status": "open"} for f in golden["expected_findings"]]
    validation = {"gate": evaluate_g1(findings, "2026-11-10T00:00:00Z"), "findings": findings, "approvals": []}
    for record in records:
        if record["kind"] == "gate_decision" and record.get("gate") == "G1":
            validation = record_decision(validation, record)
    return validation


def g2_of(order, records=None):
    records = order_records(ALL, order, 1) if records is None else records
    extraction, validation = extraction_of(order), validation_of(order, records)
    plan = cli.build_plan(extraction, PACKAGES[CURRENT[order]], REGISTER, "2026-11-10T00:00:00Z", validation, AS_OF)
    attach_to_plan(plan, order, RECORDS, set(CURRENT))
    apply_access_type(plan, records)
    g2 = evaluate_g2(extraction["product"], extraction, validation, plan, records, "2026-11-10T00:00:00Z")
    g2_milestone_state(plan, g2)
    return g2, plan


def test_seeded_records_are_synthetic_and_never_name_a_real_person():
    assert SEEDED["synthetic"] is True and SEEDED["synthetic_mark"] == "SYNTHETIC — NOT REAL DATA"
    assert {r["order_id"] for r in ALL} == {"SYN-EPL-0013", "SYN-WAV-0013", "SYN-WAV-0003"}
    assert all(r["recorded_by"].endswith("(synthetic)") for r in ALL)
    assert len({r["record_id"] for r in ALL}) == len(ALL)


def test_g2_rules_list_the_approved_requirements():
    ids = [r["id"] for r in gate_rule("G2")["requirements"]]
    assert ids == ["g1_passed", "design_approved", "ports_assigned", "optical_path_assigned", "cross_connects",
                   "third_party_segments", "site_access", "route_diversity", "protection_design"]


@pytest.mark.parametrize("order", ["SYN-EPL-0013", "SYN-WAV-0013"])
def test_clean_orders_pass_g1_and_g2_by_human_decision(order):
    g2, plan = g2_of(order)
    assert g2["recommendation"] == "pass" and g2["unmet_requirements"] == []
    assert g2["human_decision"]["approval"]["approver"].endswith("(synthetic)")
    states = {m["key"]: m["state"] for m in plan["milestones"]}
    assert (states["intake_g1"], states["g2"]) == ("completed", "completed")
    supplier = next(m for m in plan["milestones"] if m["key"] in ("third_party_access", "supplier_segments_foc"))
    assert supplier["applicability"] == "not_applicable"  # on-net confirmed by an Engineering record
    assert all(a["status"] == "resolved" for a in plan["actions"] if a["action"] == "confirm_access_type")


def test_wav_0003_fails_g2_on_exactly_the_shared_cross_connect():
    g2, plan = g2_of("SYN-WAV-0003")
    assert g2["recommendation"] == "block" and g2["unmet_requirements"] == ["cross_connects"]
    [cross] = [r for r in g2["requirements"] if r["id"] == "cross_connects"]
    assert cross["missing"] == ["shared_resource_blocked:XC-SYN-AURORA-A"]
    assert g2["human_decision"] is None
    g2_milestone = next(m for m in plan["milestones"] if m["key"] == "g2")
    assert (g2_milestone["state"], g2_milestone["blocked_by"]) == ("blocked", ["cross_connects"])


def test_an_order_without_records_is_blocked_and_says_why():
    g2, _ = g2_of("SYN-EPL-0014", records=[])
    assert g2["recommendation"] == "block"
    assert {"g1_passed", "design_approved", "ports_assigned", "cross_connects", "site_access"} <= set(
        g2["unmet_requirements"])


@pytest.mark.parametrize("kind, requirement", [
    ("design_approval", "design_approved"),
    ("port_assignment", "ports_assigned"),
    ("cross_connect_request", "cross_connects"),
    ("site_access_confirmation", "site_access"),
    ("access_contacts_confirmation", "site_access"),
    ("access_type", "third_party_segments"),
])
def test_each_missing_record_fails_its_requirement(kind, requirement):
    records = [r for r in order_records(ALL, "SYN-EPL-0013", 1) if r["kind"] != kind]
    g2, _ = g2_of("SYN-EPL-0013", records)
    assert requirement in g2["unmet_requirements"] and g2["human_decision"] is None


@pytest.mark.parametrize("order, reason", [("SYN-EPL-0009", "no_date"), ("SYN-EPL-0008", "forecast_only")])
def test_supplier_without_a_firm_foc_blocks_g2(order, reason):
    """D65: a supplier with no date blocks, not only a forecast."""
    records = [dict(r, order_id=order) for r in order_records(ALL, "SYN-EPL-0013", 1)
               if not (r["kind"] == "gate_decision" and r.get("gate") == "G2")]
    g2, _ = g2_of(order, records)
    [segments] = [r for r in g2["requirements"] if r["id"] == "third_party_segments"]
    assert segments["result"] == "unmet" and segments["missing"] == [f"supplier_firm_foc:D1:{reason}"]


def test_route_diversity_and_protection_follow_the_contract():
    records = [r for r in order_records(ALL, "SYN-WAV-0013", 1) if r["kind"] != "diversity_evidence"]
    g2, _ = g2_of("SYN-WAV-0013", records)
    assert "route_diversity" in g2["unmet_requirements"]
    [protection] = [r for r in g2["requirements"] if r["id"] == "protection_design"]
    assert protection["result"] == "not_applicable"  # unprotected


def test_a_g2_approval_is_not_applied_to_a_block_recommendation():
    records = [r for r in order_records(ALL, "SYN-WAV-0013", 1) if r["kind"] != "design_approval"]
    g2, _ = g2_of("SYN-WAV-0013", records)
    assert g2["recommendation"] == "block" and g2["human_decision"] is None
    assert any("not applied" in w for w in g2["warnings"])


def test_a_g1_approval_never_passes_a_blocked_order():
    validation = {"gate": evaluate_g1([{"finding_id": "F1", "rule_id": "X", "field_key": "x", "gate": "G1",
                                        "severity": "critical", "status": "open"}], "t"), "findings": []}
    record = copy.deepcopy(next(r for r in ALL if r["kind"] == "gate_decision" and r["gate"] == "G1"))
    with pytest.raises(ValueError):
        record_decision(validation, record)
