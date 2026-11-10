"""Checks on the rules files and the two synthetic example orders.

Run from the repo root:  .venv/bin/python -m pytest -q
"""

import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data" / "synthetic"))

import generate  # noqa: E402

EXAMPLES = ROOT / "data" / "synthetic" / "examples"
ORDER_DIRS = sorted(p for p in EXAMPLES.iterdir() if p.is_dir())
MARK = "SYNTHETIC — NOT REAL DATA"

# Real organizations that must never appear in synthetic data (CLAUDE.md rule 4).
# This list is a guard, not customer data; extend it as needed.
REAL_NAMES = ["google", "amazon", "microsoft", "meta platforms", "oracle", "apple", "equinix",
              "digital realty", "lumen", "zayo", "verizon", "at&t", "telefonica", "claro", "telmex"]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def golden(order_dir: Path) -> dict:
    return load(order_dir / "golden.json")


@pytest.mark.parametrize("name", ["fields.common.json", "fields.epl.json", "fields.wavelength.json"])
def test_rules_files_match_schema(name):
    schema = load(ROOT / "schemas" / "field_rules.schema.json")
    errors = list(Draft202012Validator(schema).iter_errors(load(ROOT / "rules" / name)))
    assert not errors, [e.message for e in errors]


def test_two_examples_one_per_product():
    assert sorted(golden(d)["order"]["product"] for d in ORDER_DIRS) == ["EPL", "WAVELENGTH"]


@pytest.mark.parametrize("order_dir", ORDER_DIRS, ids=lambda p: p.name)
class TestExampleOrder:
    def test_golden_matches_schema(self, order_dir):
        schema = load(ROOT / "schemas" / "golden_label.schema.json")
        errors = list(Draft202012Validator(schema).iter_errors(golden(order_dir)))
        assert not errors, [e.message for e in errors]

    def test_every_document_carries_the_synthetic_mark(self, order_dir):
        g = golden(order_dir)
        on_disk = sorted(p.name for p in (order_dir / "documents").iterdir())
        assert on_disk == sorted(d["filename"] for d in g["documents"])
        for name in on_disk:
            text = (order_dir / "documents" / name).read_text(encoding="utf-8")
            assert text.startswith(f"> **{MARK}**"), name
            assert text.rstrip().endswith(f"> **{MARK}**"), name

    def test_no_real_company_names(self, order_dir):
        for path in order_dir.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8").lower()
                hits = [n for n in REAL_NAMES if n in text]
                assert not hits, f"{path.name}: {hits}"

    def test_customer_and_tenant_are_labeled_synthetic(self, order_dir):
        order = golden(order_dir)["order"]
        assert "(synthetic)" in order["customer"]
        assert "(synthetic)" in order["tenant"]

    def test_every_critical_field_has_exactly_one_label(self, order_dir):
        g = golden(order_dir)
        expected = sorted(generate.load_rules(g["order"]["product"]))
        assert sorted(f["field_key"] for f in g["expected_fields"]) == expected

    def test_no_value_without_a_source(self, order_dir):
        for f in golden(order_dir)["expected_fields"]:
            if f["raw_value"] is not None:
                assert f["sources"], f["field_key"]
            if f["expected_status"] == "missing":
                assert not f["sources"], f["field_key"]

    def test_findings_point_at_defective_fields(self, order_dir):
        g = golden(order_dir)
        status = {f["field_key"]: f["expected_status"] for f in g["expected_fields"]}
        for finding in g["expected_findings"]:
            assert status[finding["field_key"]] in ("missing", "contradictory"), finding
            if status[finding["field_key"]] == "contradictory":
                assert len({s["raw_value"] for s in finding["conflicting_values"]}) > 1

    def test_gate_blocks_exactly_when_there_is_a_critical_finding(self, order_dir):
        g = golden(order_dir)
        critical = [f["finding_id"] for f in g["expected_findings"] if f["severity"] == "critical"]
        assert g["expected_gate"]["blocking_finding_ids"] == critical
        assert g["expected_gate"]["recommendation"] == ("block" if critical else "pass")

    def test_no_committed_date_is_invented(self, order_dir):
        g = golden(order_dir)
        committed = next(f for f in g["expected_fields"] if f["field_key"] == "dates.committed")
        assert committed["raw_value"] is None
        assert not any(d["is_commitment"] for d in g["expected_dates"])


def test_generation_is_deterministic(tmp_path):
    generate.generate(tmp_path)
    for order_dir in ORDER_DIRS:
        for path in order_dir.rglob("*"):
            if path.is_file():
                fresh = tmp_path / path.relative_to(EXAMPLES)
                assert fresh.read_text(encoding="utf-8") == path.read_text(encoding="utf-8"), path.name
