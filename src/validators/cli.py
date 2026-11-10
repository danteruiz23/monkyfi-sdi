"""Run the validators and gate G1 over an extraction run. From the repo root:

    .venv/bin/python -m src.validators.cli --run runs/eval-meta
    .venv/bin/python evals/run.py --predictions runs/eval-meta

Reads <run>/<order>/v<N>/extraction.json (written by src.extract.cli), writes validation.json next
to it and adds findings, gate and reopened validations to prediction.json. No model call: the same
extraction always gives the same findings. SYNTHETIC — NOT REAL DATA.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from ..extract.prediction import to_prediction
from ..i18n import LANGUAGES
from .. import ROOT
from ..ingest import read_package
from ..ingest.documents import now_utc
from .segregation import load_register
from .evaluate import add_to_prediction, render_finding, validate_version


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def version_dirs(run: Path, orders: list[str] | None) -> list[Path]:
    found = [p.parent for p in run.glob("*/v*/extraction.json") if not orders or p.parent.parent.name in orders]
    return sorted(found, key=lambda p: (p.parent.name, int(p.name[1:])))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validators and gate G1 over an extraction run")
    parser.add_argument("--run", type=Path, required=True, help="directory with <order>/v<N>/extraction.json")
    parser.add_argument("--orders", nargs="*", help="only these order ids")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None,
                        help="evaluation date for due dates, YYYY-MM-DD (default: today)")
    parser.add_argument("--language", choices=LANGUAGES, default="en", help="language of the printed findings")
    parser.add_argument("--quiet", action="store_true", help="one line per order version")
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "synthetic",
                        help="dataset with manifest.json (where each order's documents are)")
    parser.add_argument("--customers", type=Path, default=None,
                        help="customer register of the tenant (default: <data>/customers.json)")
    args = parser.parse_args(argv)

    directories = version_dirs(args.run, args.orders)
    if not directories:
        print(f"Not run: no extraction.json under {args.run}", file=sys.stderr)
        return 2
    as_of, evaluated_at = args.as_of or date.today(), now_utc()
    manifest = _read(args.data / "manifest.json")
    paths = {o["order_id"]: args.data / o["path"] for o in manifest["orders"]}
    customers = load_register(args.customers or args.data / "customers.json")[manifest["tenant"]]
    print("SYNTHETIC — NOT REAL DATA", flush=True)
    failures = 0
    for directory in directories:
        order_id, version_no = directory.parent.name, int(directory.name[1:])
        try:
            extraction = _read(directory / "extraction.json")
            earlier = directory.parent / f"v{version_no - 1}"
            previous = _read(earlier / "extraction.json") if (earlier / "extraction.json").exists() else None
            previous_validation = _read(earlier / "validation.json") if (earlier / "validation.json").exists() else None
            package = paths[order_id] / f"v{version_no}" / "documents"
            documents = read_package(package) if package.is_dir() else None
            validation = validate_version(extraction, as_of=as_of, evaluated_at=evaluated_at, previous=previous,
                                          previous_validation=previous_validation, documents=documents,
                                          customers=customers)
            prediction = add_to_prediction(to_prediction(extraction), validation)
        except (ValueError, KeyError, OSError) as exc:
            failures += 1
            print(f"  {order_id} v{version_no}: FAILED — {exc}", flush=True)
            continue
        for name, document in (("validation.json", validation), ("prediction.json", prediction)):
            (directory / name).write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        gate, change = validation["gate"], validation["version_change"]
        line = f"  {order_id} v{version_no}: G1 {gate['recommendation']}, {len(validation['findings'])} finding(s)"
        if change is not None:
            line += f", reopened {len(change['reopened_validations'])} of {len(extraction['fields'])} validations"
        print(line + "".join(f" [{w}]" for w in validation["warnings"]), flush=True)
        if args.quiet:
            continue
        for finding in validation["findings"]:
            text = render_finding(finding, args.language)
            print(f"      {text['finding_id']} {finding['rule_id']} [{text['severity']}] {text['description']} "
                  f"→ {text['owner']} / {text['resolving_party']}, {text['due_date']}: {text['action']}", flush=True)
        if change is not None and change["reopened_validations"]:
            print(f"      reopened: {', '.join(change['reopened_validations'])}", flush=True)
    print(f"Done: {len(directories) - failures} validated, {failures} failed.", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
