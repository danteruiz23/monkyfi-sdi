"""Planner over a run: types every date of each order version and writes plan.json next to
extraction.json; adds the dates section to prediction.json for the eval runner.

Usage, from the repo root:
    .venv/bin/python -m src.planner.cli --run runs/eval-meta [--orders SYN-WAV-0001 ...] [--show]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..ingest.documents import SYNTHETIC_MARK, now_utc, read_package
from .dates import PLANNER_VERSION, classify_dates, to_prediction_dates
from .milestones import build_milestones

ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def supplier_register(data: Path) -> list[str]:
    return [s["name"] for s in _read(data / "seed" / "supplier.json")]


def build_plan(extraction: dict, documents, suppliers: list[str], evaluated_at: str,
               validation: dict | None = None) -> dict:
    # No approval records exist yet (data/synthetic/seed/approval.json is empty), so no order
    # commitment is usable as the order's committed date.
    dates = classify_dates(extraction, documents, suppliers, approvals={})
    plan = build_milestones(extraction.get("product"), extraction, dates, validation)
    return {
        "synthetic": True,
        "synthetic_mark": SYNTHETIC_MARK,
        "order_dir_id": extraction["order_dir_id"],
        "version_no": extraction["version_no"],
        "run": {"planner_version": PLANNER_VERSION, "evaluated_at": evaluated_at},
        "product": extraction.get("product"),
        "dates": dates,
        "milestones": plan["milestones"],
        "actions": plan["actions"],
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
    order = plan["dates"]["order"]
    print(f"      order dates: requested {order['requested']} · forecast {order['forecast']} · "
          f"committed {order['committed']} · committed awaiting approval {order['committed_awaiting_approval']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Phase 4 planner: date typing over an extraction run")
    parser.add_argument("--run", type=Path, required=True, help="directory with <order>/v<N>/extraction.json")
    parser.add_argument("--orders", nargs="*", help="only these order ids")
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "synthetic")
    parser.add_argument("--show", action="store_true", help="print every date mention with its sentence")
    args = parser.parse_args(argv)

    manifest = _read(args.data / "manifest.json")
    paths = {o["order_id"]: args.data / o["path"] for o in manifest["orders"]}
    suppliers = supplier_register(args.data)
    directories = sorted(p.parent for p in args.run.glob("*/v*/extraction.json")
                         if not args.orders or p.parent.parent.name in args.orders)
    if not directories:
        print(f"Not run: no extraction.json under {args.run}", file=sys.stderr)
        return 2
    print(SYNTHETIC_MARK, flush=True)
    evaluated_at, failures = now_utc(), 0
    for directory in directories:
        order_id, version_no = directory.parent.name, int(directory.name[1:])
        try:
            extraction = _read(directory / "extraction.json")
            package = paths[order_id] / f"v{version_no}" / "documents"
            documents = read_package(package) if package.is_dir() else None
            validation = _read(directory / "validation.json") if (directory / "validation.json").exists() else None
            plan = build_plan(extraction, documents, suppliers, evaluated_at, validation)
        except (ValueError, KeyError, OSError) as exc:
            failures += 1
            print(f"  {order_id} v{version_no}: FAILED — {exc}", flush=True)
            continue
        _write(directory / "plan.json", plan)
        prediction_path = directory / "prediction.json"
        if prediction_path.exists():
            prediction = _read(prediction_path)
            prediction["dates"] = to_prediction_dates(plan["dates"])
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
