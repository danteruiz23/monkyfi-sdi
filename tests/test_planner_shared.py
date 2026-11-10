"""Phase 4, case 7 (UC07 minimal slice): a blocked shared resource flags every linked order, once."""

from __future__ import annotations

import json
from datetime import date

import pytest

from conftest import DATA, GOLDENS, VERSION_DIRS, load

from test_planner_dates import PACKAGES, email
from test_planner_dependencies import plan_of
from test_planner_milestones import IDS

from src.planner import cli
from src.planner.shared import attach_to_plan, link_resources, resource_mentions

AS_OF = date(2026, 11, 10)
AURORA = ["SYN-WAV-0001", "SYN-WAV-0002", "SYN-WAV-0003"]


def run_dataset():
    """Every order's current version, linked across the whole dataset as one run."""
    current = {}
    for directory in VERSION_DIRS:
        current[directory.parent.name] = max(current.get(directory.parent.name, directory), directory,
                                             key=lambda d: int(d.name[1:]))
    mentions = [m for order, d in current.items() for m in resource_mentions(order, PACKAGES[d])]
    records = link_resources(mentions, AS_OF)
    plans = {}
    for order, d in current.items():
        plans[order] = attach_to_plan(plan_of(d), order, records, set(current))
    return current, records, plans


CURRENT, RECORDS, PLANS = run_dataset()


def test_one_record_for_the_aurora_cross_connect():
    assert list(RECORDS) == ["XC-SYN-AURORA-A"]
    record = RECORDS["XC-SYN-AURORA-A"]
    assert (record["kind"], record["is_blocked"], record["linked_order_ids"]) == ("cross_connect", True, AURORA)
    assert record["action"]["owner"] == "provisioning" and record["action"]["linked_order_ids"] == AURORA


@pytest.mark.parametrize("order", sorted({d.parent.name for d in VERSION_DIRS}))
def test_shared_resources_equal_the_labels_on_every_order(order):
    golden = GOLDENS[CURRENT[order]]
    key = lambda r: (r["shared_resource_id"], r["kind"], r["is_blocked"], tuple(r["linked_order_ids"]))  # noqa: E731
    assert sorted(map(key, PLANS[order]["shared_resources"])) == sorted(map(key, golden["shared_resources"]))


def test_the_blocker_shows_on_all_3_orders_with_one_shared_action():
    action_ids = set()
    for order in AURORA:
        plan = PLANS[order]
        [flag] = plan["shared_resources"]
        assert flag["is_blocked"] and flag["linked_not_in_run"] == []
        cross = next(m for m in plan["milestones"] if m["key"] == "cross_connects_az")
        assert cross["state"] == "blocked" and "XC-SYN-AURORA-A" in cross["blocked_by"]
        [action] = [a for a in plan["actions"] if a.get("shared_resource") == "XC-SYN-AURORA-A"]
        action_ids.add(action["action_id"])
    assert action_ids == {"SR-XC-SYN-AURORA-A"}  # one request, not one per order


def test_a_linked_order_outside_the_run_is_still_named():
    directory = CURRENT["SYN-WAV-0002"]
    records = link_resources(resource_mentions("SYN-WAV-0002", PACKAGES[directory]), AS_OF)
    plan = attach_to_plan(plan_of(directory), "SYN-WAV-0002", records, {"SYN-WAV-0002"})
    assert plan["shared_resources"][0]["linked_not_in_run"] == ["SYN-WAV-0001", "SYN-WAV-0003"]


def test_the_latest_email_decides_and_blocked_wins_within_it():
    older = email("Hello,\nThe request XC-TEST-ONE for SYN-WAV-0001 was accepted the request yesterday.\nOps",
                  "05_email_01.pdf")
    newer = email("Hello,\nThe request XC-TEST-ONE for SYN-WAV-0001 is on hold at the operator.\nOps", "06_email_02.pdf")
    older.pages[0] = type(older.pages[0])(1, older.pages[0].text.replace("Subject:", "Sent: 2026-11-01 10:00 UTC\nSubject:"))
    newer.pages[0] = type(newer.pages[0])(1, newer.pages[0].text.replace("Subject:", "Sent: 2026-11-03 10:00 UTC\nSubject:"))
    mentions = resource_mentions("SYN-WAV-0001", [older, newer])
    assert link_resources(mentions, AS_OF)["XC-TEST-ONE"]["state"] == "blocked"
    cleared = link_resources(resource_mentions("SYN-WAV-0001", [older]), AS_OF)["XC-TEST-ONE"]
    assert (cleared["state"], cleared["action"]) == ("cleared", None)


def test_planner_cli_links_orders_across_the_run(tmp_path):
    for order in AURORA:
        golden = GOLDENS[CURRENT[order]]
        target = tmp_path / order / "v1"
        target.mkdir(parents=True)
        plan = plan_of(CURRENT[order])
        # The CLI needs an extraction; build it the same way as the plan fixture.
        from test_planner_dates import golden_extraction
        extraction = golden_extraction(golden)
        expected = {f["field_key"]: f for f in golden["expected_fields"]}
        for field in extraction["fields"]:
            field["status"] = expected[field["field_key"]]["expected_status"]
            field["normalized_value"] = expected[field["field_key"]]["normalized_value"]
        (target / "extraction.json").write_text(json.dumps(extraction), encoding="utf-8")
        (target / "prediction.json").write_text(json.dumps({"external_order_id": order}), encoding="utf-8")
        assert plan["milestones"]
    assert cli.main(["--run", str(tmp_path), "--as-of", "2026-11-10"]) == 0
    for order in AURORA:
        prediction = load(tmp_path / order / "v1" / "prediction.json")
        assert prediction["shared_resources"] == [{"shared_resource_id": "XC-SYN-AURORA-A", "kind": "cross_connect",
                                                   "is_blocked": True, "linked_order_ids": AURORA}]
