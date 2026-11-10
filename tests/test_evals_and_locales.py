"""The eval runner scores correctly, and the locale files stay in step."""

import json

from jsonschema import Draft202012Validator, FormatChecker

import run as evals
from conftest import DATA, MANIFEST, MARK, ROOT, load

UNITS = evals.load_units(DATA)
SPLIT = [u for u in UNITS if u["split"] != "adversarial"]
ADVERSARIAL = [u for u in UNITS if u["split"] == "adversarial"]


def score(predictor):
    predictions = {evals.key(u): predictor(u["golden"]) for u in UNITS}
    return {r["eval"]: r for r in evals.run_all(SPLIT, ADVERSARIAL, predictions, MANIFEST)}


def test_runner_reports_denominators_without_predictions(capsys, tmp_path):
    assert evals.main(["--out", str(tmp_path / "latest.json")]) == 0
    output = capsys.readouterr().out
    assert "NOT RUN" in output and "Scorer self-check" in output and "OK" in output
    results = json.loads((tmp_path / "latest.json").read_text())["results"]
    assert {r["status"] for r in results} == {"NOT RUN"}
    by_name = {r["eval"]: r for r in results}
    assert by_name["Gate G1: not-ready orders passed"]["denominator"] > 0
    assert by_name["Segregation and embedded content (adversarial)"]["denominator"] == 8


def test_perfect_predictor_passes_every_scored_eval():
    results = score(evals.perfect_prediction)
    assert not [name for name, r in results.items() if r["status"] == "FAIL"]
    assert results["Critical field extraction"]["numerator"] == results["Critical field extraction"]["denominator"]
    assert results["Gate G1: not-ready orders passed"]["numerator"] == 0
    assert results["Invented committed dates"]["numerator"] == 0


def test_blind_predictor_fails_the_release_blockers():
    results = score(evals.blind_prediction)
    gate = results["Gate G1: not-ready orders passed"]
    assert gate["status"] == "FAIL" and gate["numerator"] == gate["denominator"] > 0
    assert results["Discrepancy recall (critical)"]["numerator"] == 0
    assert results["Segregation and embedded content (adversarial)"]["status"] == "FAIL"


def test_an_invented_committed_date_is_caught():
    def inventing(golden):
        prediction = evals.perfect_prediction(golden)
        prediction["dates"].append({"doc_id": "email_01", "date": "2027-06-30", "type": "committed", "scope": "order"})
        return prediction
    assert score(inventing)["Invented committed dates"]["status"] == "FAIL"


def test_a_lowered_severity_is_caught():
    def lowering(golden):
        prediction = evals.perfect_prediction(golden)
        for finding in prediction["findings"]:
            finding["severity"] = "info"
        return prediction
    assert score(lowering)["Severity never lowered"]["status"] == "FAIL"


def test_reference_predictions_match_the_prediction_schema():
    validator = Draft202012Validator(load(ROOT / "schemas" / "prediction.schema.json"), format_checker=FormatChecker())
    for unit in UNITS:
        for predictor in (evals.perfect_prediction, evals.blind_prediction):
            assert not [e.message for e in validator.iter_errors(predictor(unit["golden"]))]


def test_runner_scores_predictions_from_a_directory(tmp_path):
    for unit in UNITS:
        path = tmp_path / "run" / unit["order_id"] / f"v{unit['version_no']}" / "prediction.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(evals.blind_prediction(unit["golden"])))
    assert evals.main(["--predictions", str(tmp_path / "run"), "--out", str(tmp_path / "latest.json")]) == 1


# ------------------------------------------------------------------------ locales

def keys(node, prefix=""):
    for key, value in node.items():
        yield from keys(value, f"{prefix}{key}.") if isinstance(value, dict) else [f"{prefix}{key}"]


def test_locales_have_the_same_keys_and_no_empty_strings():
    en, es = load(ROOT / "locales" / "en.json"), load(ROOT / "locales" / "es.json")
    assert sorted(keys(en)) == sorted(keys(es))
    assert en["app"]["synthetic_mark"] == MARK
    for locale in (en, es):
        stack = [locale]
        while stack:
            for value in stack.pop().values():
                if isinstance(value, dict):
                    stack.append(value)
                else:
                    assert isinstance(value, str) and value.strip()
