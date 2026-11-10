"""Checks on the rules files and the synthetic dataset (Phase 1 exit criteria)."""

import filecmp
from collections import Counter

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pypdf import PdfReader

import generate
from conftest import DATA, GOLDENS, MANIFEST, MARK, ROOT, VERSION_DIRS, load, version_id

# Real organizations that must never appear in synthetic data (CLAUDE.md rule 4).
# This list is a guard, not customer data; extend it as needed.
REAL_NAMES = ["google", "amazon", "microsoft", "meta platforms", "oracle", "apple", "equinix", "digital realty",
              "lumen", "zayo", "verizon", "at&t", "telefonica", "claro", "telmex", "alibaba", "tencent", "ibm",
              "cisco", "ciena", "nokia", "huawei", "colt", "orange", "vodafone", "telxius", "cirion", "liberty"]

G1 = load(ROOT / "rules" / "gates.json")["gates"]["G1"]
ORDERS = MANIFEST["orders"]


def validate(schema_name: str, instance) -> list[str]:
    schema = load(ROOT / "schemas" / schema_name)
    return [e.message for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance)]


def pdf_pages(path) -> list[str]:
    return [page.extract_text() for page in PdfReader(str(path)).pages]


# ------------------------------------------------------------------------- rules

@pytest.mark.parametrize("name", ["fields.common.json", "fields.epl.json", "fields.wavelength.json"])
def test_rules_files_match_schema(name):
    assert not validate("field_rules.schema.json", load(ROOT / "rules" / name))


def test_handoff_interface_fields_are_per_endpoint():  # D25
    for product, keys in (("EPL", ["interface.type", "interface.optic", "interface.connector"]),
                          ("WAVELENGTH", ["interface.client_interface", "interface.optic", "interface.optic_reach",
                                          "interface.connector"])):
        rules = generate.load_rules(product)
        for key in keys:
            assert f"a_end.{key}" in rules and f"z_end.{key}" in rules and key not in rules


def test_g1_rule_never_requires_verified():  # D28
    assert G1["requires_verified"] is False
    assert "verified" not in G1["blocking_statuses"] and "pending" not in G1["blocking_statuses"]
    assert set(G1["blocking_statuses"]) == {"missing", "contradictory"}


# --------------------------------------------------------------------- composition

def test_dataset_composition():  # SPEC 11.1, D14
    assert len(ORDERS) == 44
    by = Counter((o["product"], o["category"]) for o in ORDERS)
    for product in ("EPL", "WAVELENGTH"):
        assert (by[product, "clean"], by[product, "defect"], by[product, "adversarial"]) == (5, 13, 4)
    assert Counter(o["split"] for o in ORDERS) == {"dev": 24, "eval": 12, "adversarial": 8}
    assert all((o["split"] == "adversarial") == (o["category"] == "adversarial") for o in ORDERS)


def test_split_is_separated_by_customer():
    customers = {split: {o["customer"] for o in ORDERS if o["split"] == split} for split in ("dev", "eval", "adversarial")}
    assert not customers["dev"] & customers["eval"]
    assert not customers["adversarial"] & (customers["dev"] | customers["eval"])


def test_three_wavelength_project_stays_on_one_side():
    project = [o for o in ORDERS if o["project"]]
    assert len(project) == 3 and {o["product"] for o in project} == {"WAVELENGTH"}
    assert len({o["split"] for o in project}) == 1
    for o in project:
        golden = GOLDENS[DATA / o["path"] / "v1"]
        assert sorted(golden["shared_resources"][0]["linked_order_ids"]) == sorted(p["order_id"] for p in project)
        assert golden["shared_resources"][0]["is_blocked"] is True


def test_all_16_mandatory_cases_have_data():
    cases = MANIFEST["mandatory_cases"]
    assert sorted(map(int, cases)) == list(range(1, 17))
    for number, case in cases.items():
        assert case["orders"] or case["events"], f"case {number} has no data"


def test_defect_orders_have_one_or_two_seeded_defects():
    for path, golden in GOLDENS.items():
        count = len(golden["seeded_defects"])
        category = golden["order"]["category"]
        if category == "clean":
            assert count == 0, path
        elif golden["order"]["version_no"] == max(o["versions"][-1] for o in ORDERS
                                                   if o["order_id"] == golden["order"]["external_order_id"]):
            assert 1 <= count <= 2, (path, count)


def test_handoffs_differ_between_ends_in_at_least_three_orders():  # D25
    differing, defective = set(), set()
    for golden in GOLDENS.values():
        fields = {f["field_key"]: f for f in golden["expected_fields"]}
        for key, field in fields.items():
            if key.startswith("a_end.interface."):
                other = fields[key.replace("a_end.", "z_end.")]
                if field["raw_value"] and other["raw_value"] and field["raw_value"] != other["raw_value"]:
                    differing.add(golden["order"]["external_order_id"])
        if any(".interface." in f["field_key"] for f in golden["expected_findings"]):
            defective.add(golden["order"]["external_order_id"])
    assert len(differing | defective) >= 3, differing
    assert defective, "no order where the handoff difference is the defect"


def test_events_match_schema():
    assert len(MANIFEST["events"]) == 3
    for event in MANIFEST["events"]:
        assert not validate("simulated_event.schema.json", load(DATA / event["path"]))


def test_no_real_company_names():
    for path in [*DATA.rglob("*.md"), *DATA.rglob("*.json"), *DATA.rglob("*.py")]:
        text = path.read_text(encoding="utf-8").lower()
        hits = [n for n in REAL_NAMES if f" {n} " in f" {text} ".replace("\n", " ").replace(",", " ").replace(".", " ")]
        assert not hits, f"{path}: {hits}"


# ------------------------------------------------------------- per order version

@pytest.mark.parametrize("version_dir", VERSION_DIRS, ids=version_id)
class TestOrderVersion:
    def test_golden_matches_schema(self, version_dir):
        assert not validate("golden_label.schema.json", GOLDENS[version_dir])

    def test_every_pdf_page_carries_the_synthetic_mark(self, version_dir):
        golden = GOLDENS[version_dir]
        on_disk = sorted(p.name for p in (version_dir / "documents").iterdir())
        assert on_disk == sorted(d["filename"] for d in golden["documents"])
        for doc in golden["documents"]:
            pages = pdf_pages(version_dir / "documents" / doc["filename"])
            assert len(pages) == doc["pages"]
            for text in pages:
                assert text.count(MARK) >= 2, doc["filename"]
                assert not [n for n in REAL_NAMES if f" {n} " in f" {text.lower()} "], doc["filename"]

    def test_markdown_copies_carry_the_synthetic_mark(self, version_dir):
        names = sorted(p.stem for p in (version_dir / "markdown").iterdir())
        assert names == sorted(d["filename"][:-4] for d in GOLDENS[version_dir]["documents"])
        for path in (version_dir / "markdown").iterdir():
            text = path.read_text(encoding="utf-8")
            assert text.startswith(f"> **{MARK}**") and text.rstrip().endswith(f"> **{MARK}**"), path.name

    def test_package_is_complete(self, version_dir):  # SPEC 11.1, D31
        golden = GOLDENS[version_dir]
        types = Counter(d["doc_type"] for d in golden["documents"] if not d["foreign"])
        assert types["quote"] == types["order_form"] == types["technical_annex"] == 1
        fields = {f["field_key"]: f for f in golden["expected_fields"]}
        needs_loa = any(fields[f"{end}.cross_connect.required"]["normalized_value"] is True for end in ("a_end", "z_end"))
        assert types["loa_cfa"] == (1 if needs_loa else 0)
        assert 1 <= sum(d["doc_type"] == "email" for d in golden["documents"]) <= 3

    def test_customer_and_tenant_are_labeled_synthetic(self, version_dir):
        order = GOLDENS[version_dir]["order"]
        assert "(synthetic)" in order["customer"] and "(synthetic)" in order["tenant"]

    def test_every_critical_field_has_exactly_one_label(self, version_dir):
        golden = GOLDENS[version_dir]
        expected = sorted(generate.load_rules(golden["order"]["product"]))
        assert sorted(f["field_key"] for f in golden["expected_fields"]) == expected

    def test_no_value_without_a_source(self, version_dir):
        golden = GOLDENS[version_dir]
        pages = {d["doc_id"]: d["pages"] for d in golden["documents"]}
        for f in golden["expected_fields"]:
            if f["raw_value"] is not None:
                assert f["sources"], f["field_key"]
            if f["expected_status"] == "missing":
                assert not f["sources"], f["field_key"]
            for source in f["sources"]:
                assert 1 <= source["page"] <= pages[source["doc_id"]], f["field_key"]

    def test_source_values_are_on_the_cited_pdf_page(self, version_dir):
        golden = GOLDENS[version_dir]
        files = {d["doc_id"]: d["filename"] for d in golden["documents"]}
        text = {doc_id: [" ".join(p.split()) for p in pdf_pages(version_dir / "documents" / name)]
                for doc_id, name in files.items()}
        for f in golden["expected_fields"]:
            for source in f["sources"]:
                assert " ".join(source["raw_value"].split()) in text[source["doc_id"]][source["page"] - 1], \
                    (f["field_key"], source)

    def test_findings_match_defective_fields_exactly(self, version_dir):
        golden = GOLDENS[version_dir]
        status = {f["field_key"]: f["expected_status"] for f in golden["expected_fields"]}
        defective = {key for key, value in status.items() if value in G1["blocking_statuses"]}
        # A segregation finding (SEG-*, Phase 7) can stand without a defective field (D35).
        field_findings = {f["field_key"] for f in golden["expected_findings"]
                          if not f["rule_id"].startswith("SEG-") or f["field_key"] in defective}
        assert field_findings == defective
        for finding in golden["expected_findings"]:
            if status[finding["field_key"]] == "contradictory":
                assert len({s["raw_value"] for s in finding["conflicting_values"]}) > 1

    def test_g1_passes_on_consistency_not_on_verification(self, version_dir):  # D28
        golden = GOLDENS[version_dir]
        statuses = {f["expected_status"] for f in golden["expected_fields"]}
        assert "verified" not in statuses, "no label may depend on a field being verified"
        blocking = [f["finding_id"] for f in golden["expected_findings"]
                    if f["severity"] in G1["blocking_severities"]]
        assert golden["expected_gate"]["blocking_finding_ids"] == blocking
        assert golden["expected_gate"]["recommendation"] == ("block" if blocking else "pass")
        segregation = [f for f in golden["expected_findings"] if f["rule_id"].startswith("SEG-")]
        if not statuses & set(G1["blocking_statuses"]) and not segregation:
            # Every field is consistent and merely pending (or not applicable): G1 passes.
            assert statuses <= {"pending", "not_applicable"}
            assert golden["expected_gate"]["recommendation"] == "pass"
        for finding in segregation:  # another customer's data is critical by rule (D20)
            assert finding["severity"] == "critical" and golden["expected_gate"]["recommendation"] == "block"

    def test_clean_orders_have_no_findings(self, version_dir):
        golden = GOLDENS[version_dir]
        if golden["order"]["category"] == "clean":
            assert not golden["expected_findings"] and golden["expected_gate"]["recommendation"] == "pass"

    def test_only_the_carrier_commitment_is_the_committed_date(self, version_dir):  # D26
        golden = GOLDENS[version_dir]
        types = {d["doc_id"]: d["doc_type"] for d in golden["documents"]}
        committed = next(f for f in golden["expected_fields"] if f["field_key"] == "dates.committed")
        commitments = [d for d in golden["expected_dates"] if d["is_commitment"]]
        for d in commitments:
            assert d["type"] == "committed" and d["scope"] == "order" and types[d["doc_id"]] == "order_form"
            assert d["date"] == committed["normalized_value"]
        assert bool(commitments) == (committed["raw_value"] is not None)
        for d in golden["expected_dates"]:
            if types[d["doc_id"]] == "email":
                assert not d["is_commitment"], "an email never creates an order commitment"

    def test_version_change_reopens_only_changed_fields(self, version_dir):
        golden = GOLDENS[version_dir]
        change = golden["expected_version_change"]
        assert (change is None) == (golden["order"]["version_no"] == 1)
        if change:
            assert change["reopened_validations"] == [c["field_key"] for c in change["changed_fields"]]
            assert change["changed_fields"] and all(c["previous"] != c["current"] for c in change["changed_fields"])

    def test_adversarial_content_is_in_the_package(self, version_dir):
        golden = GOLDENS[version_dir]
        attack = golden["adversarial"]
        assert (attack is not None) == (golden["order"]["category"] == "adversarial")
        if attack and attack["attack"] == "embedded_instruction":
            name = next(d["filename"] for d in golden["documents"] if d["doc_id"] == attack["doc_id"])
            text = " ".join(" ".join(pdf_pages(version_dir / "documents" / name)).split())
            assert " ".join(attack["content"].split()) in text
        if attack and attack["attack"] == "other_customer_document":
            assert any(f["rule_id"] == "SEG-OTHER-CUSTOMER" and f["severity"] == "critical"
                       for f in golden["expected_findings"])


# ------------------------------------------------------------------- determinism

def test_generation_is_deterministic(tmp_path):
    generate.generate(tmp_path)
    for name in ("orders", "events"):
        comparison = filecmp.dircmp(DATA / name, tmp_path / name)
        stack = [comparison]
        while stack:
            current = stack.pop()
            assert not current.left_only and not current.right_only, (current.left_only, current.right_only)
            _, mismatch, errors = filecmp.cmpfiles(current.left, current.right, current.common_files, shallow=False)
            assert not mismatch and not errors, mismatch
            stack += current.subdirs.values()
    assert load(tmp_path / "manifest.json") == MANIFEST
