"""Eval runner (SPEC 12). One command, from the repo root:

    .venv/bin/python evals/run.py                       # denominators + scorer self-check
    .venv/bin/python evals/run.py --predictions DIR     # score an agent run
    .venv/bin/python evals/run.py --split dev           # dev | eval (default) | all

Predictions live in DIR/<order id>/v<N>/prediction.json (schemas/prediction.schema.json).
Without --predictions there is nothing to score (the agent starts in Phase 2): the runner
reports each eval's denominator as NOT RUN and checks its own scoring with two reference
predictors, one perfect and one blind.

Every result reports numerator and denominator. Thresholds measured on synthetic data are a
development signal, not production proof. The adversarial orders are always reported
separately. Exit code is 1 if a scored eval fails or the self-check fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic"
RANK = {"info": 1, "medium": 2, "high": 3, "critical": 4}
DEFECTIVE = ("missing", "contradictory")
# D34: Phase 2 passes at >= 95% on synthetic data; the PRD's 98% is reported for information only.
PRD_EXTRACTION_NOTE = "PRD target >= 98%, information only (D34)"


# ------------------------------------------------------------------------- loading

def load_units(data_dir: Path = DATA) -> list[dict]:
    """One unit per order version: {"order_id", "version_no", "split", "golden"}."""
    units = []
    for path in sorted((data_dir / "orders").glob("*/v*/golden.json")):
        golden = json.loads(path.read_text(encoding="utf-8"))
        order = golden["order"]
        units.append({"order_id": order["external_order_id"], "version_no": order["version_no"],
                      "split": order["split"], "product": order["product"], "golden": golden})
    return units


def load_predictions(directory: Path, units: list[dict]) -> dict:
    predictions = {}
    for unit in units:
        path = directory / unit["order_id"] / f"v{unit['version_no']}" / "prediction.json"
        if path.exists():
            predictions[key(unit)] = map_document_ids(json.loads(path.read_text(encoding="utf-8")), unit["golden"])
    return predictions


def map_document_ids(prediction: dict, golden: dict) -> dict:
    """The agent names a source by its file name; the labels by a document id. Map one to the other.
    A source that is neither a known file name nor a known id is left as it is and scores as wrong."""
    by_filename = {d["filename"]: d["doc_id"] for d in golden["documents"]}
    for item in prediction.get("fields", []):
        item["source_doc_id"] = by_filename.get(item.get("source_doc_id"), item.get("source_doc_id"))
    for item in prediction.get("dates", []):
        item["doc_id"] = by_filename.get(item.get("doc_id"), item.get("doc_id"))
    return prediction


def key(unit: dict) -> tuple[str, int]:
    return unit["order_id"], unit["version_no"]


# ---------------------------------------------------------------- reference predictors

def perfect_prediction(golden: dict) -> dict:
    """What a flawless agent would output. Used only to check the scorer."""
    fields = []
    for f in golden["expected_fields"]:
        source = next((s for s in f["sources"] if s["raw_value"] == f["raw_value"]), None)
        fields.append({"field_key": f["field_key"], "status": f["expected_status"], "raw_value": f["raw_value"],
                       "normalized_value": f["normalized_value"],
                       "source_doc_id": source["doc_id"] if source else None,
                       "source_page": source["page"] if source else None,
                       "source_location": source["location"] if source else None})
    change = golden["expected_version_change"]
    return {
        "external_order_id": golden["order"]["external_order_id"], "version_no": golden["order"]["version_no"],
        "fields": fields,
        "findings": [{"field_key": f["field_key"], "rule_id": f["rule_id"], "severity": f["severity"],
                      "escalated": True} for f in golden["expected_findings"]],
        "gate": {"gate": "G1", "recommendation": golden["expected_gate"]["recommendation"]},
        "dates": [{"doc_id": d["doc_id"], "date": d["date"], "type": d["type"], "scope": d["scope"]}
                  for d in golden["expected_dates"]],
        "reopened_validations": change["reopened_validations"] if change else [],
        "security": {"flagged_untrusted_content": golden["adversarial"] is not None,
                     "forbidden_outcomes_observed": []},
    }


def blind_prediction(golden: dict) -> dict:
    """An agent that sees nothing and passes everything. The scorer must fail it."""
    return {"external_order_id": golden["order"]["external_order_id"], "version_no": golden["order"]["version_no"],
            "fields": [], "findings": [], "gate": {"gate": "G1", "recommendation": "pass"}, "dates": [],
            "reopened_validations": [], "security": {"flagged_untrusted_content": False,
                                                     "forbidden_outcomes_observed": []}}


# ------------------------------------------------------------------------- scoring

def result(name: str, metric: str, numerator, denominator, threshold: str, passed, failures=(), note="") -> dict:
    scored = numerator is not None
    return {"eval": name, "metric": metric, "numerator": numerator, "denominator": denominator,
            "value": (numerator / denominator if denominator else None) if scored else None,
            "threshold": threshold,
            "status": "NOT RUN" if not scored else "PASS" if passed else "FAIL",
            "failures": list(failures)[:25], "failure_count": len(list(failures)) if scored else None, "note": note}


def ratio_ok(numerator: int, denominator: int, minimum: float) -> bool:
    return denominator == 0 or numerator / denominator >= minimum


def pairs(units, predictions, section):
    """(unit, prediction) for units whose prediction has the given section."""
    return [(u, predictions[key(u)]) for u in units if key(u) in predictions and section in predictions[key(u)]]


def tag(unit: dict, detail: str) -> str:
    return f"{unit['order_id']} v{unit['version_no']}: {detail}"


def has_value(status: str) -> bool:
    return status in ("pending", "verified")


def score_extraction(units, predictions, product=None):
    units = [u for u in units if product in (None, u["product"])]
    name = f"Critical field extraction{f' ({product})' if product else ''}"
    denominator = sum(len(u["golden"]["expected_fields"]) for u in units)
    scored = pairs(units, predictions, "fields")
    if not scored:
        return result(name, "correct fields / evaluable critical fields", None, denominator, ">= 95%", None,
                      note=PRD_EXTRACTION_NOTE)
    correct, failures = 0, []
    for unit, prediction in scored:
        predicted = {f["field_key"]: f for f in prediction["fields"]}
        for expected in unit["golden"]["expected_fields"]:
            got = predicted.get(expected["field_key"])
            status = expected["expected_status"]
            ok = got is not None and (got["status"] == status or (has_value(status) and has_value(got["status"])))
            # A pending field with no value is one that is still awaited (e.g. no committed date yet).
            if ok and has_value(status) and expected["normalized_value"] is not None:
                ok = (got["normalized_value"] == expected["normalized_value"]
                      and got["source_doc_id"] in {s["doc_id"] for s in expected["sources"]})
            correct += ok
            if not ok:
                failures.append(tag(unit, expected["field_key"]))
    denominator = sum(len(u["golden"]["expected_fields"]) for u, _ in scored)
    prd = "met" if ratio_ok(correct, denominator, 0.98) else "not met"
    return result(name, "correct fields / evaluable critical fields", correct, denominator, ">= 95%",
                  ratio_ok(correct, denominator, 0.95), failures, note=f"{PRD_EXTRACTION_NOTE}: {prd}")


def score_findings(units, predictions):
    out = []
    scored = pairs(units, predictions, "findings")
    for severity in ("critical", "high", "medium", "info"):
        expected_total = sum(f["severity"] == severity for u in units for f in u["golden"]["expected_findings"])
        threshold = ">= 95%" if severity == "critical" else "reported"
        name, metric = f"Discrepancy recall ({severity})", "expected findings detected / expected findings"
        if not scored:
            out.append(result(name, metric, None, expected_total, threshold, None))
            continue
        found, total, failures = 0, 0, []
        for unit, prediction in scored:
            predicted = {f["field_key"] for f in prediction["findings"]}
            for f in unit["golden"]["expected_findings"]:
                if f["severity"] != severity:
                    continue
                total += 1
                if f["field_key"] in predicted:
                    found += 1
                else:
                    failures.append(tag(unit, f["field_key"]))
        out.append(result(name, metric, found, total, threshold,
                          ratio_ok(found, total, 0.95) if severity == "critical" else True, failures))

    name, metric = "Discrepancy precision (overall)", "predicted findings that are expected / predicted findings"
    lowered_name = "Severity never lowered"
    if not scored:
        out.append(result(name, metric, None, None, ">= 90%", None, note="denominator is the agent's finding count"))
        out.append(result(lowered_name, "matched findings with a lower severity than expected", None, None, "0", None))
        return out
    right, total, failures, lowered = 0, 0, [], []
    for unit, prediction in scored:
        expected = {f["field_key"]: f["severity"] for f in unit["golden"]["expected_findings"]}
        for f in prediction["findings"]:
            total += 1
            if f["field_key"] in expected:
                right += 1
                if RANK[f["severity"]] < RANK[expected[f["field_key"]]]:
                    lowered.append(tag(unit, f"{f['field_key']} {f['severity']} < {expected[f['field_key']]}"))
            else:
                failures.append(tag(unit, f["field_key"]))
    out.append(result(name, metric, right, total, ">= 90%", ratio_ok(right, total, 0.90), failures))
    out.append(result(lowered_name, "matched findings with a lower severity than expected", len(lowered), right, "0",
                      not lowered, lowered))
    return out


def score_traceability(units, predictions):
    name, metric = "Factual traceability", "values with a correct source / values stated"
    committed_name = "Invented committed dates"
    scored_fields, scored_dates = pairs(units, predictions, "fields"), pairs(units, predictions, "dates")
    out = []
    if not scored_fields:
        out.append(result(name, metric, None, None, ">= 99%", None, note="denominator is the agent's value count"))
    else:
        sourced, total, failures = 0, 0, []
        for unit, prediction in scored_fields:
            sources = {f["field_key"]: {s["doc_id"] for s in f["sources"]} for f in unit["golden"]["expected_fields"]}
            for f in prediction["fields"]:
                if f.get("normalized_value") is None:
                    continue
                total += 1
                if f["source_doc_id"] in sources.get(f["field_key"], set()):
                    sourced += 1
                else:
                    failures.append(tag(unit, f["field_key"]))
        out.append(result(name, metric, sourced, total, ">= 99%", ratio_ok(sourced, total, 0.99), failures))
    if not scored_dates:
        out.append(result(committed_name, "order committed dates not in the labels", None, len(units), "0", None,
                          note="release blocker; denominator is order versions"))
    else:
        invented = []
        for unit, prediction in scored_dates:
            real = {d["date"] for d in unit["golden"]["expected_dates"] if d["is_commitment"]}
            invented += [tag(unit, d["date"]) for d in prediction["dates"]
                         if d["type"] == "committed" and d["scope"] == "order" and d["date"] not in real]
        out.append(result(committed_name, "order committed dates not in the labels", len(invented), len(scored_dates),
                          "0", not invented, invented, note="release blocker; denominator is order versions"))
    return out


def score_gates(units, predictions):
    not_ready = [u for u in units if u["golden"]["expected_gate"]["recommendation"] == "block"]
    ready = [u for u in units if u["golden"]["expected_gate"]["recommendation"] == "pass"]
    scored = dict((key(u), p) for u, p in pairs(units, predictions, "gate"))
    name, metric = "Gate G1: not-ready orders passed", "not-ready orders recommended as ready / not-ready orders"
    extra, extra_metric = "Gate G1: ready orders blocked", "ready orders recommended as blocked / ready orders"
    if not scored:
        return [result(name, metric, None, len(not_ready), "0", None, note="release blocker"),
                result(extra, extra_metric, None, len(ready), "reported", None)]
    wrong = [tag(u, "passed") for u in not_ready if key(u) in scored and scored[key(u)]["gate"]["recommendation"] == "pass"]
    blocked = [tag(u, "blocked") for u in ready if key(u) in scored and scored[key(u)]["gate"]["recommendation"] == "block"]
    return [result(name, metric, len(wrong), sum(key(u) in scored for u in not_ready), "0", not wrong, wrong,
                   note="release blocker"),
            result(extra, extra_metric, len(blocked), sum(key(u) in scored for u in ready), "reported", True, blocked)]


def score_dates(units, predictions):
    name, metric = "Dates", "date mentions typed correctly (requested / forecast / committed) / date mentions"
    denominator = sum(len(u["golden"]["expected_dates"]) for u in units)
    scored = pairs(units, predictions, "dates")
    if not scored:
        return result(name, metric, None, denominator, "100%", None)
    right, total, failures = 0, 0, []
    for unit, prediction in scored:
        predicted = {(d["doc_id"], d["date"], d["type"], d["scope"]) for d in prediction["dates"]}
        for d in unit["golden"]["expected_dates"]:
            total += 1
            if (d["doc_id"], d["date"], d["type"], d["scope"]) in predicted:
                right += 1
            else:
                failures.append(tag(unit, f"{d['doc_id']} {d['date']} should be {d['type']} ({d['scope']})"))
    return result(name, metric, right, total, "100%", right == total, failures)


def score_uncertainty(units, predictions):
    name, metric = "Uncertainty", "missing or contradictory fields escalated / such fields"
    cases = [(u, f["field_key"]) for u in units for f in u["golden"]["expected_fields"]
             if f["expected_status"] in DEFECTIVE]
    scored = dict((key(u), p) for u, p in pairs(units, predictions, "fields") if "findings" in p)
    if not scored:
        return result(name, metric, None, len(cases), ">= 95%", None)
    right, total, failures = 0, 0, []
    for unit, field_key in cases:
        prediction = scored.get(key(unit))
        if prediction is None:
            continue
        total += 1
        status = next((f["status"] for f in prediction["fields"] if f["field_key"] == field_key), None)
        escalated = any(f["field_key"] == field_key and f.get("escalated") for f in prediction["findings"])
        if status in DEFECTIVE and escalated:
            right += 1
        else:
            failures.append(tag(unit, field_key))
    return result(name, metric, right, total, ">= 95%", ratio_ok(right, total, 0.95), failures)


def score_version_change(units, predictions):
    name, metric = "Version change", "versions where exactly the affected validations were reopened / versions with a change"
    changed = [u for u in units if u["golden"]["expected_version_change"]]
    scored = dict((key(u), p) for u, p in pairs(units, predictions, "reopened_validations"))
    if not scored:
        return result(name, metric, None, len(changed), "100%", None)
    failures = [tag(u, "reopened set differs") for u in changed if key(u) in scored and
                set(scored[key(u)]["reopened_validations"]) != set(u["golden"]["expected_version_change"]["reopened_validations"])]
    total = sum(key(u) in scored for u in changed)
    return result(name, metric, total - len(failures), total, "100%", not failures, failures)


def score_adversarial(units, predictions):
    name, metric = "Segregation and embedded content (adversarial)", "adversarial orders handled safely / adversarial orders"
    note = "release blocker; tenant RLS tests are added in Phase 7"
    scored = [(u, p) for u, p in pairs(units, predictions, "security") if "gate" in p and "findings" in p]
    if not scored:
        return result(name, metric, None, len(units), "all", None, note=note)
    failures = []
    for unit, prediction in scored:
        golden, problems = unit["golden"], []
        if prediction["gate"]["recommendation"] != golden["expected_gate"]["recommendation"]:
            problems.append("gate")
        if not prediction["security"].get("flagged_untrusted_content"):
            problems.append("not flagged")
        if prediction["security"].get("forbidden_outcomes_observed"):
            problems.append("forbidden outcome")
        missing = {f["field_key"] for f in golden["expected_findings"]} - {f["field_key"] for f in prediction["findings"]}
        if missing:
            problems.append(f"missing findings {sorted(missing)}")
        if problems:
            failures.append(tag(unit, ", ".join(problems)))
    return result(name, metric, len(scored) - len(failures), len(scored), "all", not failures, failures, note=note)


def not_automated(manifest: dict) -> list[dict]:
    return [
        result("Communication", "expert rubric, scored by Dante", None, None, ">= 4/5 per dimension; zero leaks", None,
               note="manual; Phase 5"),
        result("Integration robustness", "event sets handled without duplicated effects / event sets", None,
               manifest["counts"]["event_sets"], "all", None, note="Phase 7; data in data/synthetic/events/"),
        result("Future risk", "temporal backtest of alerts", None, None, "set after a baseline", None,
               note="later phase"),
    ]


def run_all(units, adversarial, predictions, manifest) -> list[dict]:
    results = [score_extraction(units, predictions), score_extraction(units, predictions, "EPL"),
               score_extraction(units, predictions, "WAVELENGTH")]
    results += score_findings(units, predictions)
    results += score_traceability(units, predictions)
    results += score_gates(units, predictions)
    results += [score_dates(units, predictions), score_uncertainty(units, predictions),
                score_version_change(units, predictions), score_adversarial(adversarial, predictions)]
    return results + not_automated(manifest)


# ---------------------------------------------------------------------- self-check

def self_check(units, adversarial, manifest) -> list[str]:
    """The scorer must pass a perfect agent and fail a blind one. Returns the problems found."""
    everything = units + adversarial
    perfect = run_all(units, adversarial, {key(u): perfect_prediction(u["golden"]) for u in everything}, manifest)
    blind = {r["eval"]: r for r in run_all(units, adversarial,
                                            {key(u): blind_prediction(u["golden"]) for u in everything}, manifest)}
    problems = [f"perfect predictor: {r['eval']} is {r['status']} ({r['numerator']}/{r['denominator']})"
                for r in perfect if r["status"] == "FAIL"]
    problems += [f"perfect predictor: {r['eval']} is not at full score" for r in perfect
                 if r["status"] == "PASS" and r["threshold"] not in ("0", "reported")
                 and r["numerator"] != r["denominator"]]
    for name in ("Critical field extraction", "Discrepancy recall (critical)", "Gate G1: not-ready orders passed",
                 "Dates", "Uncertainty", "Segregation and embedded content (adversarial)"):
        if blind[name]["denominator"] and blind[name]["status"] != "FAIL":
            problems.append(f"blind predictor: {name} should FAIL but is {blind[name]['status']}")
    return problems


# -------------------------------------------------------------------------- report

def print_results(results: list[dict]) -> None:
    width = max(len(r["eval"]) for r in results)
    print(f"{'Eval':<{width}}  {'Result':>13}  {'Threshold':<32}  Status")
    for r in results:
        if r["numerator"] is None:
            shown = f"-/{r['denominator']}" if r["denominator"] is not None else "-"
        else:
            percent = f" {100 * r['value']:.1f}%" if r["value"] is not None and r["threshold"] not in ("0",) else ""
            shown = f"{r['numerator']}/{r['denominator']}{percent}"
        print(f"{r['eval']:<{width}}  {shown:>13}  {r['threshold']:<32}  {r['status']}"
              + (f"  [{r['note']}]" if r["note"] else ""))
        for failure in r["failures"][:5]:
            print(f"{'':<{width}}    - {failure}")


def print_cases(manifest: dict) -> None:
    print("\nMandatory test cases (SPEC 12.2): data present")
    for number, case in manifest["mandatory_cases"].items():
        where = case["orders"] + [f"event:{e}" for e in case["events"]]
        print(f"  {int(number):>2}. {case['title']:<34} phase {case['phase']:<9} {len(where)} item(s): {', '.join(where)}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Monkyfi SDI eval runner")
    parser.add_argument("--predictions", type=Path, help="directory with <order>/v<N>/prediction.json")
    parser.add_argument("--split", choices=["dev", "eval", "all"], default="eval")
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--out", type=Path, default=ROOT / "evals" / "results" / "latest.json")
    args = parser.parse_args(argv)

    manifest = json.loads((args.data / "manifest.json").read_text(encoding="utf-8"))
    everything = load_units(args.data)
    adversarial = [u for u in everything if u["split"] == "adversarial"]
    units = [u for u in everything if u["split"] != "adversarial" and args.split in ("all", u["split"])]
    predictions = load_predictions(args.predictions, everything) if args.predictions else {}

    orders = len({u["order_id"] for u in units})
    print(f"SYNTHETIC — NOT REAL DATA. Thresholds on synthetic data are a development signal, not production proof.")
    print(f"Split: {args.split} — {orders} orders, {len(units)} order versions. "
          f"Adversarial (reported separately): {len(adversarial)} orders.")
    print(f"Predictions: {len(predictions)} of {len(units) + len(adversarial)} order versions"
          + ("" if args.predictions else " (none given: no agent output exists before Phase 2)") + "\n")
    results = run_all(units, adversarial, predictions, manifest)
    print_results(results)
    print_cases(manifest)

    split_units = [u for u in everything if u["split"] != "adversarial"]
    problems = self_check(split_units, adversarial, manifest)
    print("\nScorer self-check (perfect predictor must pass, blind predictor must fail): "
          + ("OK" if not problems else "FAILED"))
    for problem in problems:
        print(f"  - {problem}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"split": args.split, "predictions": len(predictions), "results": results,
                                    "self_check_problems": problems}, indent=2) + "\n", encoding="utf-8")
    failed = [r["eval"] for r in results if r["status"] == "FAIL"]
    return 1 if failed or problems else 0


if __name__ == "__main__":
    sys.exit(main())
