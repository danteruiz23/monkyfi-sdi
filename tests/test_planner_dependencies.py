"""Phase 4 supplier dependencies, follow-up (D55) and not estimable (UC05, cases 5 and 6)."""

from __future__ import annotations

from datetime import date

import pytest

from conftest import DATA, GOLDENS, VERSION_DIRS, load

from test_planner_dates import PACKAGES, golden_extraction
from test_planner_milestones import IDS

import run as evals
from src.planner import cli
from src.planner.cli import to_prediction_dependency
from src.planner.dependencies import dependency_graph, supplier_dependencies
from src.planner.dates import classify_dates

REGISTER = load(DATA / "seed" / "supplier.json")
AS_OF = date(2026, 11, 10)


def plan_of(directory, as_of=AS_OF, register=REGISTER):
    golden = GOLDENS[directory]
    extraction = golden_extraction(golden)
    expected = {f["field_key"]: f for f in golden["expected_fields"]}
    for field in extraction["fields"]:
        field["status"] = expected[field["field_key"]]["expected_status"]
        field["normalized_value"] = expected[field["field_key"]]["normalized_value"]
    return cli.build_plan(extraction, PACKAGES[directory], register, "2026-11-10T00:00:00Z", None, as_of)


PLANS = {d: plan_of(d) for d in VERSION_DIRS}


def test_supplier_register_has_the_d55_thresholds():
    assert {(s["follow_up_threshold_days"], s["escalation_threshold_days"]) for s in REGISTER} == {(3, 5)}


@pytest.mark.parametrize("directory", VERSION_DIRS, ids=IDS)
def test_dependencies_equal_the_labels(directory):
    """All 48 versions: same supplier dependencies as labeled, with no extra one."""
    golden = GOLDENS[directory]
    by_filename = {d["filename"]: d["doc_id"] for d in golden["documents"]}
    predicted = sorted(tuple(p[k] for k in evals.DEPENDENCY_KEYS) + (by_filename[p["source_doc_id"]],)
                       for p in map(to_prediction_dependency, PLANS[directory]["dependencies"]))
    labeled = sorted(tuple(d[k] for k in evals.DEPENDENCY_KEYS) + (d["source_doc_id"],)
                     for d in golden["expected_dependencies"])
    assert predicted == labeled


@pytest.mark.parametrize("directory", VERSION_DIRS, ids=IDS)
def test_missing_information_is_never_a_delay(directory):
    plan = PLANS[directory]
    for d in plan["dependencies"]:
        assert d["delay_assessment"] in ("unknown", "not_assessed")
        if d["supplier_date"] is None:
            assert (d["supplier_input"], d["delay_assessment"]) == ("missing", "unknown")
            assert plan["supplier_inputs"]["status"] == "missing"
    assert plan["supplier_inputs"]["delay_assessment"] in ("unknown", "not_assessed")
    # Supplier inputs are never a delivery forecast (D61, D62).
    assert plan["delivery_forecast"] == {"status": "not_estimable", "date": None, "reason": "no_standard_interval"}


def test_case_6_supplier_without_a_date_is_not_estimable_with_a_follow_up():
    plan = PLANS[DATA / "orders" / "SYN-EPL-0009" / "v1"]
    [d] = plan["dependencies"]
    assert (d["supplier_date"], d["supplier_input"], d["follow_up_expected"]) == (None, "missing", True)
    assert plan["supplier_inputs"] == {"status": "missing", "missing": ["D1"], "delay_assessment": "unknown"}
    delivery = next(m for m in plan["milestones"] if m["key"] == "delivery")
    assert (delivery["forecast_status"], delivery["forecast_reason"]) == ("not_estimable", "no_standard_interval")


def test_case_5_tentative_supplier_date_is_a_dependency_forecast_with_its_assumption():
    plan = PLANS[DATA / "orders" / "SYN-WAV-0001" / "v1"]
    [d] = plan["dependencies"]
    assert (d["supplier_date"], d["supplier_date_type"], d["follow_up_expected"]) == ("2027-01-22", "forecast", True)
    assert any("building entry permit" in a for a in d["assumptions"])
    assert plan["dates"]["order"]["committed"] == []


def test_firm_supplier_foc_needs_no_follow_up_and_stays_on_the_dependency():
    plan = PLANS[DATA / "orders" / "SYN-WAV-0011" / "v1"]
    [d] = plan["dependencies"]
    assert (d["supplier_date_type"], d["follow_up_expected"], d["follow_up"]) == ("committed", False, None)
    assert plan["dates"]["order"]["committed"] == [] and not [a for a in plan["actions"] if a.get("dependency")]


@pytest.mark.parametrize("as_of, state, owner, due", [
    (date(2026, 11, 7), "not_due", "supplier_management", "2026-11-10"),
    (date(2026, 11, 10), "follow_up_due", "supplier_management", "2026-11-10"),
    (date(2026, 11, 12), "escalation_due", "sdm", "2026-11-12"),
])
def test_follow_up_after_3_business_days_and_escalation_after_5(as_of, state, owner, due):
    """SYN-WAV-0001: the supplier's last email was sent on Thursday 2026-11-05."""
    plan = plan_of(DATA / "orders" / "SYN-WAV-0001" / "v1", as_of=as_of)
    [d] = plan["dependencies"]
    assert (d["follow_up"]["anchor"], d["follow_up"]["first_follow_up_on"], d["follow_up"]["escalation_on"]) == (
        "2026-11-05", "2026-11-10", "2026-11-12")
    assert d["follow_up"]["state"] == state
    [action] = [a for a in plan["actions"] if a.get("dependency") == "D1"]
    assert (action["owner"], action["due_date"]) == (owner, due)
    assert (action["anchor"], action["anchor_kind"]) == ("2026-11-05", "last_supplier_email")
    expected_history = ([{"event": "first_follow_up_due_not_answered", "on": "2026-11-10",
                          "owner": "supplier_management"}] if state == "escalation_due" else [])
    assert action["history"] == expected_history


def test_thresholds_are_per_supplier():
    register = [dict(s, follow_up_threshold_days=1, escalation_threshold_days=2) for s in REGISTER]
    plan = plan_of(DATA / "orders" / "SYN-WAV-0001" / "v1", register=register)
    assert plan["dependencies"][0]["follow_up"]["first_follow_up_on"] == "2026-11-06"


def test_graph_links_the_supplier_dependency_to_the_supplier_milestone():
    plan = PLANS[DATA / "orders" / "SYN-WAV-0001" / "v1"]
    assert {"from": "D1", "to": "supplier_segments_foc", "kind": "supplier"} in plan["dependency_graph"]["edges"]
    assert {"from": "supplier_segments_foc", "to": "g2", "kind": "milestone"} in plan["dependency_graph"]["edges"]


def test_no_dependency_without_documents():
    golden = GOLDENS[DATA / "orders" / "SYN-WAV-0001" / "v1"]
    dates = classify_dates(golden_extraction(golden), None, [s["name"] for s in REGISTER])
    assert supplier_dependencies(dates, None, REGISTER, AS_OF) == []
    assert dependency_graph([], [])["edges"] == []


def test_access_action_is_due_in_2_business_days_by_default():
    plan = PLANS[DATA / "orders" / "SYN-WAV-0002" / "v1"]  # no supplier email: access type unknown
    [action] = [a for a in plan["actions"] if a["action"] == "confirm_access_type"]
    assert (action["owner"], action["due_date"]) == ("engineering", "2026-11-12")  # Tue 11-10 + 2 business days
