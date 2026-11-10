"""Planner over a run: dates, milestones, supplier dependencies and follow-up for each order version.
Writes plan.json next to extraction.json and adds the dates and dependencies sections to prediction.json.

Usage, from the repo root (run after the validators):
    .venv/bin/python -m src.planner.cli --run runs/eval-meta [--orders ...] [--as-of YYYY-MM-DD] [--show]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from ..ingest.documents import SYNTHETIC_MARK, now_utc, read_package
from .dates import PLANNER_VERSION, classify_dates, to_prediction_dates
from .dependencies import dependency_graph, supplier_dependencies
from .milestones import build_milestones
from .shared import attach_to_plan, link_resources, resource_mentions

ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def supplier_register(data: Path) -> list[dict]:
    return _read(data / "seed" / "supplier.json")


def to_prediction_dependency(d: dict) -> dict:
    """The prediction keeps the golden label's field name (order_forecast_status) so the eval can compare;
    it means only whether the supplier input is in (D62)."""
    out = {k: d[k] for k in ("source_doc_id", "kind", "supplier", "supplier_date", "supplier_date_type",
                             "follow_up_expected")}
    out["order_forecast_status"] = "estimable" if d["supplier_input"] == "complete" else "not_estimable"
    return out


FOLLOW_UP_ACTIONS = {"follow_up_due": "follow_up_supplier", "escalation_due": "escalate_supplier_follow_up",
                     "not_due": "follow_up_supplier", "anchor_unknown": "follow_up_supplier"}


def dependency_actions(dependencies: list[dict], first_id: int) -> list[dict]:
    """One open action per supplier dependency that needs a follow-up (UC05, D55)."""
    actions = []
    for d in dependencies:
        follow = d["follow_up"]
        if not follow:
            continue
        escalate = follow["state"] == "escalation_due"
        # D62: an escalation keeps the record that the first follow-up was due and not answered.
        history = [{"event": "first_follow_up_due_not_answered", "on": follow["first_follow_up_on"],
                    "owner": follow["owner"]}] if escalate else []
        actions.append({"action_id": f"A{first_id + len(actions)}", "action": FOLLOW_UP_ACTIONS[follow["state"]],
                        "milestone": None, "dependency": d["dependency_id"], "supplier": d["supplier"],
                        "owner": follow["escalate_to"] if escalate else follow["owner"],
                        "reason": follow["state"], "status": "open",
                        "due_date": follow["escalation_on"] if escalate else follow["first_follow_up_on"],
                        "anchor": follow["anchor"], "anchor_kind": "last_supplier_email", "history": history,
                        "decision": "D55"})
    return actions


def supplier_inputs(dependencies: list[dict]) -> dict:
    """D62: are all supplier inputs in? Not a delivery forecast. A missing date is unknown, never a delay."""
    missing = [d["dependency_id"] for d in dependencies if d["supplier_input"] == "missing"]
    return {"status": "missing" if missing else "complete", "missing": missing,
            "delay_assessment": "unknown" if missing else "not_assessed"}


def delivery_forecast(milestones: list[dict]) -> dict:
    """The delivery forecast. Without standard intervals (D61) it is not built from supplier inputs."""
    delivery = next((m for m in milestones if m["key"] == "delivery"), None)
    if delivery and delivery["forecast_date"]:
        return {"status": "estimated", "date": delivery["forecast_date"], "reason": None}
    return {"status": "not_estimable", "date": None, "reason": "no_standard_interval"}


def build_plan(extraction: dict, documents, register: list[dict], evaluated_at: str,
               validation: dict | None = None, as_of: date | None = None) -> dict:
    as_of = as_of or date.today()
    suppliers = [s["name"] for s in register]
    # No approval records exist yet (data/synthetic/seed/approval.json is empty), so no order
    # commitment is usable as the order's committed date.
    dates = classify_dates(extraction, documents, suppliers, approvals={})
    plan = build_milestones(extraction.get("product"), extraction, dates, validation, as_of)
    dependencies = supplier_dependencies(dates, documents, register, as_of)
    actions = plan["actions"] + dependency_actions(dependencies, len(plan["actions"]) + 1)
    inputs = supplier_inputs(dependencies)
    for m in plan["milestones"]:
        if m["key"] == "delivery" and not m["forecast_date"]:
            m["forecast_reason"] = "no_standard_interval"
    forecast = delivery_forecast(plan["milestones"])
    return {
        "synthetic": True,
        "synthetic_mark": SYNTHETIC_MARK,
        "order_dir_id": extraction["order_dir_id"],
        "version_no": extraction["version_no"],
        "run": {"planner_version": PLANNER_VERSION, "evaluated_at": evaluated_at, "as_of": as_of.isoformat()},
        "product": extraction.get("product"),
        "dates": dates,
        "milestones": plan["milestones"],
        "dependencies": dependencies,
        "dependency_graph": dependency_graph(plan["milestones"], dependencies),
        "supplier_inputs": inputs,
        "delivery_forecast": forecast,
        "actions": actions,
        "warnings": dates["warnings"] + plan["warnings"],
    }


def show(plan: dict) -> None:
    for m in plan["dates"]["mentions"]:
        extra = ""
        if m.get("commitment_status"):
            extra += f" [{m['commitment_status']}]"
        if m["assumptions"]:
            extra += f" assumptions: {' | '.join(m['assumptions'])}"
        print(f"      {m['date']} {m['type']:<9} {m['scope']:<19} {m['doc_id']} p.{m['page']} "
              f"rule={m['rule']}{extra}")
        if "sentence" in m:
            print(f"          \"{m['sentence']}\"")
    for m in plan["dates"]["ignored"]:
        print(f"      {m['date']} ignored ({m['reason']}) {m['doc_id']} p.{m['page']}: \"{m['sentence']}\"")
    for ms in plan["milestones"]:
        dates = " · ".join(f"{k} {ms[k]}" for k in ("requested_date", "forecast_date", "committed_date",
                                                    "committed_awaiting_approval") if ms[k])
        print(f"      [{ms['key']:<24}] owner={ms['owner']:<19} {ms['applicability']:<14} {ms['state']:<17}"
              f" forecast={ms['forecast_status']}{' (' + ms['forecast_reason'] + ')' if ms['forecast_reason'] else ''}"
              f"{' · ' + dates if dates else ''}{' blocked by ' + ','.join(ms['blocked_by']) if ms['blocked_by'] else ''}")
        for assumption in ms["forecast_assumptions"]:
            print(f"          assumption: {assumption}")
    for d in plan["dependencies"]:
        f = d["follow_up"]
        print(f"      {d['dependency_id']} {d['supplier']} ({d['description']}): date {d['supplier_date']} "
              f"[{d['supplier_date_type']}] · supplier input {d['supplier_input']} · delay {d['delay_assessment']}"
              + (f" · follow-up from {f['anchor']}: first {f['first_follow_up_on']}, escalate {f['escalation_on']}"
                 f" → {f['state']}" if f else " · no follow-up (firm commitment)"))
    for a in plan["actions"]:
        print(f"      action {a['action_id']} {a['action']} → {a['owner']} due {a['due_date']}")
    for r in plan.get("shared_resources", []):
        print(f"      shared {r['shared_resource_id']} ({r['kind']}): {r['state']} · linked {r['linked_order_ids']}"
              f"{' (not in run: ' + ', '.join(r['linked_not_in_run']) + ')' if r['linked_not_in_run'] else ''}"
              f" · action {r['action_id']}")
    i, f = plan["supplier_inputs"], plan["delivery_forecast"]
    print(f"      supplier inputs: {i['status']} {i['missing'] or ''} · delay {i['delay_assessment']}"
          f" · delivery forecast: {f['status']} ({f['reason']})")
    order = plan["dates"]["order"]
    print(f"      order dates: requested {order['requested']} · forecast {order['forecast']} · "
          f"committed {order['committed']} · committed awaiting approval {order['committed_awaiting_approval']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Phase 4 planner: date typing over an extraction run")
    parser.add_argument("--run", type=Path, required=True, help="directory with <order>/v<N>/extraction.json")
    parser.add_argument("--orders", nargs="*", help="only these order ids")
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "synthetic")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None,
                        help="evaluation date for follow-up states, YYYY-MM-DD (default: today)")
    parser.add_argument("--show", action="store_true", help="print every date mention with its sentence")
    args = parser.parse_args(argv)

    manifest = _read(args.data / "manifest.json")
    paths = {o["order_id"]: args.data / o["path"] for o in manifest["orders"]}
    register = supplier_register(args.data)
    directories = sorted(p.parent for p in args.run.glob("*/v*/extraction.json")
                         if not args.orders or p.parent.parent.name in args.orders)
    if not directories:
        print(f"Not run: no extraction.json under {args.run}", file=sys.stderr)
        return 2
    print(SYNTHETIC_MARK, flush=True)
    evaluated_at, failures = now_utc(), 0
    as_of = args.as_of or date.today()
    built, mentions = [], []
    for directory in directories:
        order_id, version_no = directory.parent.name, int(directory.name[1:])
        try:
            extraction = _read(directory / "extraction.json")
            package = paths[order_id] / f"v{version_no}" / "documents"
            documents = read_package(package) if package.is_dir() else None
            validation = _read(directory / "validation.json") if (directory / "validation.json").exists() else None
            plan = build_plan(extraction, documents, register, evaluated_at, validation, as_of)
        except (ValueError, KeyError, OSError) as exc:
            failures += 1
            print(f"  {order_id} v{version_no}: FAILED — {exc}", flush=True)
            continue
        built.append((directory, order_id, version_no, plan))
        latest = max(int(p.name[1:]) for p in directory.parent.glob("v*") if (p / "extraction.json").exists())
        if version_no == latest:  # a shared resource is read from each order's current version
            mentions += resource_mentions(order_id, documents)
    # UC07: one record per shared resource across the run, flagged on every linked order.
    records = link_resources(mentions, as_of)
    run_orders = {order_id for _, order_id, _, _ in built}
    for directory, order_id, version_no, plan in built:
        attach_to_plan(plan, order_id, records, run_orders)
        _write(directory / "plan.json", plan)
        prediction_path = directory / "prediction.json"
        if prediction_path.exists():
            prediction = _read(prediction_path)
            prediction["dates"] = to_prediction_dates(plan["dates"])
            prediction["dependencies"] = [to_prediction_dependency(d) for d in plan["dependencies"]]
            prediction["shared_resources"] = [{k: r[k] for k in ("shared_resource_id", "kind", "is_blocked",
                                                                  "linked_order_ids")}
                                              for r in plan["shared_resources"]]
            _write(prediction_path, prediction)
        counts = {}
        for m in plan["dates"]["mentions"]:
            counts[m["type"]] = counts.get(m["type"], 0) + 1
        print(f"  {order_id} v{version_no}: {len(plan['dates']['mentions'])} date(s) "
              f"{dict(sorted(counts.items()))}, {len(plan['dates']['ignored'])} ignored"
              + f", {sum(1 for m in plan['milestones'] if m['applicability'] != 'not_applicable')} milestone(s)"
              + "".join(f" [{w}]" for w in plan["warnings"]), flush=True)
        if args.show:
            show(plan)
    print(f"Done: {len(directories) - failures} planned, {failures} failed.", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
