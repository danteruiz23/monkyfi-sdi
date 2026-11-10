"""Phase 4 milestone plan (src/planner/milestones.py, rules/milestones.json, D56)."""

from __future__ import annotations

import pytest

from conftest import DATA, GOLDENS, ROOT, VERSION_DIRS, load

from test_planner_dates import PACKAGES, SUPPLIERS, golden_extraction

from src.planner.dates import classify_dates
from src.planner.milestones import build_milestones, milestone_rules

LOCALES = {lang: load(ROOT / "locales" / f"{lang}.json") for lang in ("en", "es")}


def golden_plan(directory, approvals=None, validation=None):
    golden = GOLDENS[directory]
    extraction = golden_extraction(golden)
    statuses = {f["field_key"]: f for f in golden["expected_fields"]}
    for field in extraction["fields"]:
        field["status"] = statuses[field["field_key"]]["expected_status"]
        field["normalized_value"] = statuses[field["field_key"]]["normalized_value"]
    dates = classify_dates(extraction, PACKAGES[directory], SUPPLIERS, approvals or {})
    return dates, build_milestones(golden["order"]["product"], extraction, dates, validation)


PLANS = {d: golden_plan(d) for d in VERSION_DIRS}
IDS = lambda d: f"{d.parent.name}-{d.name}"  # noqa: E731


def test_templates_match_d56():
    keys = {p: [m["key"] for m in ms] for p, ms in milestone_rules()["products"].items()}
    assert keys["EPL"] == ["intake_g1", "design", "port_assignment_az", "cross_connects_az", "third_party_access", "g2",
                           "provisioning", "service_tests_epl", "delivery", "acceptance"]
    assert keys["WAVELENGTH"] == ["intake_g1", "route_design_diversity", "optical_path_assignment", "cross_connects_az",
                                  "supplier_segments_foc", "g2", "provisioning", "ber_test", "delivery", "acceptance"]


def test_predecessors_name_milestones_of_the_same_product_and_have_no_cycle():
    for product, rules in milestone_rules()["products"].items():
        keys = [m["key"] for m in rules]
        for index, m in enumerate(rules):
            assert set(m["predecessors"]) <= set(keys[:index]), (product, m["key"])


def test_every_owner_role_and_milestone_has_text_in_both_languages():
    for rules in milestone_rules()["products"].values():
        for m in rules:
            for locale in LOCALES.values():
                assert m["owner"] in locale["owner_role"] and m["key"] in locale["milestone"]


@pytest.mark.parametrize("directory", VERSION_DIRS, ids=IDS)
def test_zero_critical_milestones_without_an_owner(directory):
    _, plan = PLANS[directory]
    assert plan["milestones"], "a product with no plan"
    assert all(m["owner"] for m in plan["milestones"] if m["is_critical"])


@pytest.mark.parametrize("directory", VERSION_DIRS, ids=IDS)
def test_no_milestone_is_committed_without_an_approval_and_no_forecast_without_assumptions(directory):
    _, plan = PLANS[directory]
    for m in plan["milestones"]:
        assert m["committed_date"] is None or m["commitment_approval_id"]
        if m["forecast_date"]:
            assert m["forecast_status"] == "estimated" and m["forecast_assumptions"] and m["forecast_evidence"]
        else:
            assert m["forecast_status"] == "not_estimable" and m["forecast_reason"]


@pytest.mark.parametrize("directory", VERSION_DIRS, ids=IDS)
def test_supplier_milestone_follows_the_labeled_dependency(directory):
    """Cases 5 and 6: a dated supplier dependency puts its date on the supplier milestone, as a forecast;
    a supplier without a date leaves it not estimable, never delayed."""
    golden = GOLDENS[directory]
    _, plan = PLANS[directory]
    supplier = next(m for m in plan["milestones"] if m["key"] in ("third_party_access", "supplier_segments_foc"))
    dependencies = [d for d in golden["expected_dependencies"] if d["kind"] == "supplier"]
    if not dependencies:
        assert supplier["forecast_date"] is None
        return
    [dependency] = dependencies
    assert supplier["applicability"] == "applies"
    assert supplier["forecast_date"] == dependency["supplier_date"]
    assert supplier["forecast_status"] == ("estimated" if dependency["supplier_date"] else "not_estimable")
    assert supplier["committed_date"] is None


@pytest.mark.parametrize("directory", VERSION_DIRS, ids=IDS)
def test_delivery_carries_the_contract_dates_only(directory):
    golden = GOLDENS[directory]
    dates, plan = PLANS[directory]
    delivery = next(m for m in plan["milestones"] if m["key"] == "delivery")
    requested = {d["date"] for d in golden["expected_dates"] if d["type"] == "requested" and d["doc_id"] == "order_form"}
    assert delivery["requested_date"] == (next(iter(requested)) if len(requested) == 1 else None)
    others = {d["date"] for d in golden["expected_dates"] if d["type"] == "requested" and d["doc_id"] == "quote"}
    assert delivery["requested_conflict"] == sorted(others - requested)
    assert delivery["committed_date"] is None  # no approval records in the dataset
    committed = {d["date"] for d in golden["expected_dates"] if d["type"] == "committed" and d["scope"] == "order"}
    assert delivery["committed_awaiting_approval"] == (next(iter(committed)) if committed else None)


def test_an_approved_commitment_reaches_the_delivery_milestone():
    directory = DATA / "orders" / "SYN-EPL-0014" / "v1"
    _, plan = golden_plan(directory, approvals={"2027-01-21": "APR-SYN-1"})
    delivery = next(m for m in plan["milestones"] if m["key"] == "delivery")
    assert (delivery["committed_date"], delivery["commitment_approval_id"]) == ("2027-01-21", "APR-SYN-1")


def test_intake_milestone_shows_the_g1_block_and_its_findings():
    directory = DATA / "orders" / "SYN-WAV-0001" / "v1"
    validation = {"gate": {"recommendation": "block", "human_decision": None,
                           "unmet_requirements": [{"finding_id": "F1"}]}}
    _, plan = golden_plan(directory, validation=validation)
    intake = plan["milestones"][0]
    assert (intake["key"], intake["state"], intake["blocked_by"]) == ("intake_g1", "blocked", ["F1"])


def test_a_conditional_milestone_is_never_dropped():
    _, plan = PLANS[DATA / "orders" / "SYN-WAV-0002" / "v1"]
    supplier = next(m for m in plan["milestones"] if m["key"] == "supplier_segments_foc")
    assert supplier["applicability"] == "unknown" and supplier["owner"] == "supplier_management"


@pytest.mark.parametrize("directory", VERSION_DIRS, ids=IDS)
def test_every_unknown_access_milestone_has_an_engineering_action(directory):
    """D60: no supplier email never means not applicable; the question is an Engineering action."""
    _, plan = PLANS[directory]
    for m in plan["milestones"]:
        if m["applicability"] == "unknown" and m["key"] in ("third_party_access", "supplier_segments_foc"):
            [action_id] = m["actions"]
            action = next(a for a in plan["actions"] if a["action_id"] == action_id)
            assert (action["action"], action["owner"], action["status"]) == ("confirm_access_type", "engineering", "open")
    assert len(plan["actions"]) == sum(1 for m in plan["milestones"] if m["actions"])
    for locale in LOCALES.values():
        assert all(a["action"] in locale["plan_action"] for a in plan["actions"])


def test_stage_scopes_are_1_8_2_with_service_delivery_from_order_received_to_accepted():
    """D68: Before / Service delivery (SDM scope) / After."""
    stages = load(ROOT / "rules" / "stages.json")["stages"]
    scopes = [s["scope"] for s in stages]
    assert scopes.count("before") == 1 and scopes.count("service_delivery") == 8 and scopes.count("after") == 2
    sd = [s["key"] for s in stages if s["scope"] == "service_delivery"]
    assert (sd[0], sd[-1]) == ("order_received", "accepted")
    assert all(s["key"] in LOCALES["en"]["stage"] for s in stages)
    assert set(LOCALES["en"]["stage_scope"]) == set(LOCALES["es"]["stage_scope"]) == {"before", "service_delivery", "after"}
