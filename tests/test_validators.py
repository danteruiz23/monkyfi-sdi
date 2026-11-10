"""Phase 3: findings, gate G1, override and version comparison.

The validators are deterministic, so they are tested on all 48 order versions with extraction
records produced by the golden-scripted model (no model call). What a real model's extraction
gives is measured only by evals/run.py on a real run.
"""

import copy
import json
from datetime import date

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from conftest import DATA, GOLDENS, MANIFEST, ROOT, VERSION_DIRS, load

import run as evals
from test_extraction import golden_model
from src.extract.catalog import product_rules
from src.extract.extract import extract_version
from src.extract.prediction import check, to_prediction
from src.extract.status import mark_verified
from src.i18n import LANGUAGES, t
from src.ingest import read_package
from src.ingest.documents import Document, Page
from src.providers.fake import ScriptedProvider
from src.validators import (add_to_prediction, carry_verifications, compare_versions, evaluate_g1, lower_severity,
                            override_gate, render_finding, validate, validate_version)
from src.validators import cli
from src.validators.findings import add_business_days, parties
from src.validators.segregation import core_name, load_register, other_customer_mentions
from src.validators.rules import finding_rules, gate_rule, severity_rank

AS_OF = date(2026, 11, 10)  # a Tuesday
NOW = "2026-11-10T12:00:00Z"
INTERNAL_ROLES = {"sdm", "order_management", "sales", "engineering", "provisioning"}
CUSTOMERS = load_register(DATA / "customers.json")[MANIFEST["tenant"]]


def ident(directory):
    order = GOLDENS[directory]["order"]
    return order["external_order_id"], order["version_no"]


@pytest.fixture(scope="module")
def packages():
    return {ident(d): read_package(d / "documents", ingested_at="2026-11-09T00:00:00Z") for d in VERSION_DIRS}


@pytest.fixture(scope="module")
def extractions(packages):
    out = {}
    for directory in VERSION_DIRS:
        golden, documents = GOLDENS[directory], packages[ident(directory)]
        out[ident(directory)] = extract_version(documents, ScriptedProvider(golden_model(golden, documents)),
                                                order_dir_id=ident(directory)[0], version_no=ident(directory)[1])
    return out


@pytest.fixture(scope="module")
def validations(extractions, packages):
    out = {}
    for key in sorted(extractions):
        previous = (key[0], key[1] - 1)
        out[key] = validate_version(extractions[key], as_of=AS_OF, evaluated_at=NOW, previous=extractions.get(previous),
                                    previous_validation=out.get(previous), documents=packages[key], customers=CUSTOMERS)
    return out


def golden_of(key):
    return next(g for d, g in GOLDENS.items() if ident(d) == key)


# ----------------------------------------------------------------- findings

def test_findings_match_every_label(validations):
    """Rule, field and severity of every finding, on all 48 order versions."""
    for key, validation in validations.items():
        expected = {(f["rule_id"], f["field_key"], f["severity"]) for f in golden_of(key)["expected_findings"]}
        got = {(f["rule_id"], f["field_key"], f["severity"]) for f in validation["findings"]}
        assert got == expected, key


def test_clean_orders_have_no_findings(validations):
    clean = [k for k in validations if golden_of(k)["order"]["category"] == "clean"]
    assert len(clean) == 10
    for key in clean:
        assert validations[key]["findings"] == [] and validations[key]["gate"]["recommendation"] == "pass"


def test_every_finding_has_sources_owner_due_date_and_action(validations):
    total = 0
    for key, validation in validations.items():
        check("validation.schema.json", validation)
        labels = {f["field_key"]: f for f in golden_of(key)["expected_findings"]}
        names = {d["filename"]: d["doc_id"] for d in golden_of(key)["documents"]}
        for f in validation["findings"]:
            total += 1
            assert f["owner"] in INTERNAL_ROLES and f["escalated"] and f["escalated_to"] == f["resolving_party"]
            assert f["status"] == "open" and f["due_date"] > AS_OF.isoformat()
            assert f["impact"] == ("confirmed" if f["blocks_gate"] else "possible")
            if f["rule_id"] == "SEG-OTHER-CUSTOMER":
                assert {v["raw_value"] for v in f["conflicting_values"]} & set(CUSTOMERS) - {golden_of(key)["order"]["customer"]}
            elif f["field_status"] == "contradictory":
                assert len({v["raw_value"] for v in f["conflicting_values"]}) >= 2
                got = {(names[v["filename"]], v["page"], v["raw_value"]) for v in f["conflicting_values"]}
                want = {(v["doc_id"], v["page"], v["raw_value"]) for v in labels[f["field_key"]]["conflicting_values"]}
                assert got == want, key
            else:
                assert f["conflicting_values"] == []
            for language in LANGUAGES:
                text = render_finding(f, language)
                assert all(isinstance(v, str) and v.strip() and "{" not in v for v in text.values())
    assert total == sum(len(g["expected_findings"]) for g in GOLDENS.values())


def test_only_g1_fields_that_are_missing_or_contradictory_raise_a_finding(extractions):
    """Without documents and a customer register, only field findings are raised."""
    for key, extraction in extractions.items():
        catalog = product_rules(extraction["product"])
        defective = {f["field_key"] for f in extraction["fields"]
                     if f["status"] in ("missing", "contradictory") and catalog[f["field_key"]]["gate"] == "G1"}
        assert {f["field_key"] for f in validate(extraction, AS_OF)} == defective


def test_severity_is_never_below_the_field_default(validations, extractions):
    rank = severity_rank()
    for key, validation in validations.items():
        catalog = product_rules(extractions[key]["product"])
        for f in validation["findings"]:
            assert rank[f["severity"]] >= rank[catalog[f["field_key"]]["missing_severity"]]


def test_signature_and_other_customer_are_always_critical(extractions):
    extraction = copy.deepcopy(extractions[("SYN-EPL-0002", 1)])
    for field in extraction["fields"]:
        if field["field_key"] == "signature.signatory_title":
            field.update(status="missing", raw_value=None, normalized_value=None, source=None, sources=[])
    (finding,) = validate(extraction, AS_OF)
    assert (finding["rule_id"], finding["severity"], finding["owner"]) == ("G1-SIGNATURE", "critical", "sales")
    assert finding["resolving_party"] == "sales"
    other = next(f for f in validate(extractions[("SYN-EPL-0019", 1)], AS_OF) if f["field_key"] == "customer_name")
    assert (other["rule_id"], other["severity"]) == ("SEG-OTHER-CUSTOMER", "critical")


def test_a_stale_document_gets_the_reissue_action(validations):
    findings = {f["field_key"]: f for f in validations[("SYN-EPL-0006", 2)]["findings"]}
    assert findings["order_version"]["rule_id"] == "G1-VERSION-CURRENT"
    for f in findings.values():
        assert f["action"]["key"] == "finding_action.reissue_stale_documents"
        assert f["action"]["params"]["documents"] == "03_technical_annex.pdf"
    # A contradiction between documents of the same version asks the owner which value is right.
    (capacity,) = validations[("SYN-EPL-0015", 1)]["findings"]
    assert capacity["action"]["key"] == "finding_action.confirm_correct_value"


def test_an_undetermined_product_blocks(extractions):
    extraction = copy.deepcopy(extractions[("SYN-EPL-0002", 1)])
    extraction.update(product=None, fields=[], warnings=["product could not be determined from the documents"])
    validation = validate_version(extraction, as_of=AS_OF, evaluated_at=NOW)
    assert [f["field_key"] for f in validation["findings"]] == ["product"]
    assert validation["gate"]["recommendation"] == "block"


def test_due_dates_count_business_days():
    assert add_business_days(date(2026, 11, 10), 1) == date(2026, 11, 11)
    assert add_business_days(date(2026, 11, 13), 1) == date(2026, 11, 16)  # Friday → Monday
    assert add_business_days(date(2026, 11, 12), 5) == date(2026, 11, 19)
    days = finding_rules()["due_in_business_days"]
    assert days["critical"] <= days["high"] <= days["medium"] <= days["info"]


def test_only_a_human_lowers_a_severity(validations):
    finding = validations[("SYN-EPL-0015", 1)]["findings"][0]
    with pytest.raises(ValueError):
        lower_severity(finding, "high", "", "accepted risk", NOW)
    with pytest.raises(ValueError):
        lower_severity(finding, "high", "Ana Prueba (synthetic)", " ", NOW)
    with pytest.raises(ValueError):
        lower_severity(dict(finding, severity="medium"), "critical", "Ana Prueba (synthetic)", "x", NOW)
    lowered = lower_severity(finding, "high", "Ana Prueba (synthetic)", "Quote superseded by the order form", NOW)
    assert (lowered["severity"], lowered["original_severity"], lowered["blocks_gate"]) == ("high", "critical", False)
    assert finding["severity"] == "critical" and "severity_change" not in finding


def test_internal_owner_and_resolving_party_follow_d46(validations):
    """(internal owner, resolving party) per field, as Dante decided (D46)."""
    want = {
        "order_id": ("order_management", "order_management"), "customer_name": ("order_management", "order_management"),
        "carrier_circuit_id": ("provisioning", "provisioning"),
        "signature.date": ("sales", "sales"), "cir": ("sales", "sales"), "rate": ("sales", "sales"),
        "a_end.suite_or_room": ("sdm", "customer_technical_contact_a_end"),
        "z_end.demarcation_point": ("sdm", "customer_technical_contact_z_end"),
        "z_end.meet_me_room": ("sdm", "customer_technical_contact_z_end"),
        "a_end.site_access.notice_lead_time": ("sdm", "sdm"), "a_end.technical_contact": ("sdm", "sdm"),
        "dates.requested": ("sdm", "sdm"),
        "acceptance.deemed_acceptance_clause": ("sales", "sales"), "acceptance.deemed_acceptance_period": ("sales", "sales"),
        "acceptance.required_tests": ("engineering", "engineering"), "acceptance.ber_test": ("engineering", "engineering"),
        "acceptance.ber_test_duration": ("engineering", "engineering"),
        "route_diversity.required": ("sales", "customer"), "route_diversity.reference_circuit_ids": ("sales", "customer"),
        "route_diversity.required_evidence": ("engineering", "engineering"),
        "a_end.cross_connect.loa_cfa_reference": ("provisioning", "provisioning"),
        "z_end.interface.optic": ("engineering", "engineering"), "mtu": ("engineering", "engineering"),
        "fec": ("engineering", "engineering"), "protection.switching_time": ("engineering", "engineering"),
        "latency.definition": ("engineering", "engineering"),
    }
    catalog = {**product_rules("EPL"), **product_rules("WAVELENGTH")}
    for key, expected in want.items():
        assert parties(key, catalog[key]["group"]) == expected, key
    for validation in validations.values():
        for f in validation["findings"]:
            assert (f["owner"], f["resolving_party"]) == parties(f["field_key"], catalog[f["field_key"]]["group"])
    diversity = validations[("SYN-WAV-0015", 1)]["findings"]
    assert {(f["owner"], f["resolving_party"]) for f in diversity} == {("sales", "customer"),
                                                                        ("sdm", "customer_technical_contact_z_end")}


# ----------------------------------------------------------------- customer scoping (D42)

def test_customer_register_matches_the_dataset():
    import dataset
    assert sorted(CUSTOMERS) == sorted([c[0] for c in dataset.CUSTOMERS.values()] + [dataset.OTHER_CUSTOMER])
    assert MANIFEST["tenant"] == "Carrier Alfa (synthetic)" and all(c.endswith("(synthetic)") for c in CUSTOMERS)


def test_another_customer_in_an_email_blocks_g1(validations):
    validation = validations[("SYN-WAV-0019", 1)]
    (finding,) = validation["findings"]
    assert (finding["rule_id"], finding["field_key"], finding["severity"]) == ("SEG-OTHER-CUSTOMER", "customer_name", "critical")
    assert finding["blocks_gate"] and validation["gate"]["recommendation"] == "block"
    foreign = [v for v in finding["conflicting_values"] if v["raw_value"] == "Freight Company Quebec (synthetic)"]
    assert [(v["filename"], v["page"]) for v in foreign] == [("06_email_02.pdf", 1)]
    assert finding["action"]["key"] == "finding_action.confirm_customer_and_remove_foreign_data"


def test_scoping_merges_into_an_existing_customer_finding(validations):
    for order in ("SYN-EPL-0019", "SYN-EPL-0020", "SYN-WAV-0020"):
        seg = [f for f in validations[(order, 1)]["findings"] if f["rule_id"] == "SEG-OTHER-CUSTOMER"]
        assert len(seg) == 1, order
        assert "Freight Company Quebec (synthetic)" in {v["raw_value"] for v in seg[0]["conflicting_values"]}


def test_scoping_raises_nothing_where_no_other_customer_is_named(validations):
    flagged = sorted(k[0] for k, v in validations.items() if any(f["rule_id"].startswith("SEG-") for f in v["findings"]))
    assert flagged == ["SYN-EPL-0019", "SYN-EPL-0020", "SYN-WAV-0019", "SYN-WAV-0020"]
    assert all(v["run"]["customer_scoping"] for v in validations.values())


def test_names_match_as_whole_words_with_or_without_the_suffix(packages):
    page = lambda text: [Document(filename="x.pdf", sha256="0" * 64, doc_type="email", title="Email: x",
                                  pages=[Page(1, text)], ingested_at=NOW, format="pdf")]
    assert other_customer_mentions(page("Regards, Network Lead, freight company   QUEBEC"), "Hyperscaler W (synthetic)", CUSTOMERS)
    assert not other_customer_mentions(page("Hyperscaler Wx team"), "Hyperscaler X (synthetic)", CUSTOMERS)
    assert not other_customer_mentions(page("Hyperscaler X (synthetic) only"), "Hyperscaler X (synthetic)", CUSTOMERS)
    assert core_name("Bank Lima (synthetic)") == "Bank Lima"


def test_scoping_not_run_is_stated(extractions):
    validation = validate_version(extractions[("SYN-WAV-0019", 1)], as_of=AS_OF, evaluated_at=NOW)
    assert validation["run"]["customer_scoping"] is False and validation["warnings"]
    assert validation["findings"] == []  # without the check, the email is not seen: why the CLI always runs it


# ----------------------------------------------------------------- gate G1

def test_gate_matches_every_label(validations):
    for key, validation in validations.items():
        golden = golden_of(key)
        assert validation["gate"]["recommendation"] == golden["expected_gate"]["recommendation"], key
        blocking = {f["field_key"] for f in golden["expected_findings"]
                    if f["finding_id"] in golden["expected_gate"]["blocking_finding_ids"]}
        assert {u["field_key"] for u in validation["gate"]["unmet_requirements"]} == blocking, key


def test_g1_never_requires_verified_and_only_critical_blocks(validations):
    rule = gate_rule("G1")
    assert rule["requires_verified"] is False and rule["blocking_severities"] == ["critical"]
    passed_with_findings = [k for k, v in validations.items() if v["findings"] and v["gate"]["recommendation"] == "pass"]
    assert sorted(k[0] for k in passed_with_findings) == ["SYN-EPL-0008", "SYN-WAV-0011", "SYN-WAV-0017"]
    for key in passed_with_findings:
        assert validations[key]["gate"]["non_blocking_finding_ids"] == [f["finding_id"] for f in validations[key]["findings"]]


def test_override_needs_reason_and_approver_and_keeps_the_finding(validations):
    blocked = validations[("SYN-EPL-0015", 1)]
    for approver, reason in (("", "urgent"), ("Ana Prueba (synthetic)", ""), (None, None)):
        with pytest.raises(ValueError):
            override_gate(blocked, approver, reason, NOW)
    with pytest.raises(ValueError):
        override_gate(validations[("SYN-EPL-0013", 1)], "Ana Prueba (synthetic)", "nothing to override", NOW)

    overridden = override_gate(blocked, "Ana Prueba (synthetic)", "Customer confirmed 1 Gbps by phone", NOW)
    check("validation.schema.json", overridden)
    assert overridden["gate"]["recommendation"] == "block"  # the agent's recommendation is not rewritten
    assert overridden["gate"]["unmet_requirements"] == blocked["gate"]["unmet_requirements"]
    assert overridden["gate"]["human_decision"]["outcome"] == "pass"
    (approval,) = overridden["approvals"]
    assert (approval["decision"], approval["approver"], approval["reason"]) == \
        ("override", "Ana Prueba (synthetic)", "Customer confirmed 1 Gbps by phone")
    (before,), (after,) = blocked["findings"], overridden["findings"]
    assert after["status"] == "overridden" and before["status"] == "open"
    assert {k: v for k, v in after.items() if k != "status"} == {k: v for k, v in before.items() if k != "status"}
    with pytest.raises(ValueError):
        override_gate(overridden, "Ana Prueba (synthetic)", "again", NOW)
    approval_schema = load(ROOT / "schemas" / "entities" / "approval.schema.json")
    assert set(approval) - {"created_at"} <= set(approval_schema["properties"])


def test_a_resolved_or_overridden_finding_does_not_block_but_stays(validations):
    findings = copy.deepcopy(validations[("SYN-EPL-0015", 1)]["findings"])
    findings[0]["status"] = "resolved"
    assert evaluate_g1(findings, NOW)["recommendation"] == "pass" and len(findings) == 1


# ----------------------------------------------------------------- version change

def test_only_affected_validations_are_reopened(validations, extractions):
    changed = [k for k in validations if golden_of(k)["expected_version_change"]]
    assert len(changed) == 4
    for key in changed:
        want, got = golden_of(key)["expected_version_change"], validations[key]["version_change"]
        assert set(got["reopened_validations"]) == set(want["reopened_validations"]), key
        assert got["previous_gate_recommendation"] == want["previous_gate_recommendation"]
        assert got["plan_impact"] == want["milestone_impact_expected"], key
        assert got["unchanged_validations"] == len(extractions[key]["fields"]) - len(want["reopened_validations"])
        for item in want["changed_fields"]:
            mine = next(c for c in got["changed_fields"] if c["field_key"] == item["field_key"])
            previous = extractions[(key[0], key[1] - 1)]
            old = next(f for f in previous["fields"] if f["field_key"] == item["field_key"])
            assert mine["previous"] == [old["raw_value"]]
        assert all(v["status"] == "stale" and v["superseded_by_version"] == key[1] for v in got["superseded_values"])
        assert len(got["superseded_values"]) == len(want["reopened_validations"])
        reopened = {f["field_key"] for f in validations[key]["findings"] if f["reopened"]}
        assert reopened == {f["field_key"] for f in validations[key]["findings"]} & set(want["reopened_validations"])


def test_first_versions_have_no_comparison(validations, extractions):
    assert all(v["version_change"] is None for k, v in validations.items() if k[1] == 1)
    alone = validate_version(extractions[("SYN-WAV-0016", 2)], as_of=AS_OF, evaluated_at=NOW)
    assert alone["version_change"] is None and any("previous version" in w for w in alone["warnings"])
    assert "reopened_validations" not in add_to_prediction(to_prediction(extractions[("SYN-WAV-0016", 2)]), alone)
    with pytest.raises(ValueError):
        compare_versions(extractions[("SYN-WAV-0016", 2)], extractions[("SYN-WAV-0016", 1)])
    with pytest.raises(ValueError):
        compare_versions(extractions[("SYN-WAV-0015", 1)], extractions[("SYN-WAV-0016", 2)])


def test_verified_survives_only_where_nothing_changed(extractions):
    v1, v2 = extractions[("SYN-EPL-0007", 1)], extractions[("SYN-EPL-0007", 2)]
    verified = [mark_verified(f, "Ana Prueba (synthetic)", NOW) if f["field_key"] in ("z_end.rack", "port_speed") else f
                for f in v1["fields"]]
    change = compare_versions(v1, v2)
    carried = {f["field_key"]: f for f in carry_verifications(verified, v2["fields"], change["reopened_validations"])}
    assert carried["port_speed"]["status"] == "verified" and carried["port_speed"]["verified_by"] == "Ana Prueba (synthetic)"
    assert carried["z_end.rack"]["status"] == "pending" and carried["z_end.rack"]["raw_value"] == "R-49"
    assert sum(f["status"] == "verified" for f in carried.values()) == 1


# ----------------------------------------------------------------- mandatory cases (SPEC 12.2)

@pytest.mark.parametrize("case, rule_ids", [(1, {"G1-CONSISTENCY"}), (2, {"G1-CONSISTENCY"}), (3, {"G1-REQUIRED"}),
                                             (4, {"G1-VERSION-CURRENT"}), (8, set())])
def test_mandatory_cases_of_phase_3(validations, case, rule_ids):
    orders = MANIFEST["mandatory_cases"][str(case)]["orders"]
    assert len(orders) >= 2
    for key in [k for k in validations if k[0] in orders and case in golden_of(k)["mandatory_cases"]]:
        golden, validation = golden_of(key), validations[key]
        labelled = {f["field_key"] for f in golden["expected_findings"] if f["mandatory_case"] == case}
        mine = {f["field_key"]: f for f in validation["findings"]}
        assert labelled <= set(mine), key
        assert rule_ids <= {f["rule_id"] for f in mine.values()}
        assert validation["gate"]["recommendation"] == golden["expected_gate"]["recommendation"]
        if case in (4, 8):
            assert set(validation["version_change"]["reopened_validations"]) == \
                set(golden["expected_version_change"]["reopened_validations"])
        if case == 8:  # modified after validation: v1 had passed, and the change is flagged for the plan
            assert validation["version_change"]["previous_gate_recommendation"] == "pass"
            assert validation["version_change"]["plan_impact"] is True


# ----------------------------------------------------------------- evals, CLI, locales

def test_eval_runner_scores_the_validators(validations, extractions):
    units = evals.load_units(DATA)
    split = [u for u in units if u["split"] != "adversarial"]
    predictions = {}
    for key, validation in validations.items():
        prediction = add_to_prediction(to_prediction(extractions[key]), validation)
        predictions[key] = evals.map_document_ids(prediction, golden_of(key))
    results = {r["eval"]: r for r in evals.score_findings(split, predictions) + evals.score_gates(split, predictions)
               + [evals.score_uncertainty(split, predictions), evals.score_version_change(split, predictions)]}
    for name in ("Discrepancy recall (critical)", "Discrepancy precision (overall)", "Uncertainty", "Version change"):
        assert results[name]["numerator"] == results[name]["denominator"] > 0, name
    assert results["Gate G1: not-ready orders passed"]["numerator"] == 0
    assert results["Gate G1: ready orders blocked"]["numerator"] == 0
    assert results["Severity never lowered"]["numerator"] == 0


def test_cli_writes_validation_and_prediction(extractions, tmp_path, capsys):
    for key in (("SYN-WAV-0016", 1), ("SYN-WAV-0016", 2), ("SYN-EPL-0013", 1), ("SYN-WAV-0019", 1)):
        target = tmp_path / key[0] / f"v{key[1]}"
        target.mkdir(parents=True)
        (target / "extraction.json").write_text(json.dumps(extractions[key]), encoding="utf-8")
    assert cli.main(["--run", str(tmp_path), "--as-of", "2026-11-10", "--language", "es"]) == 0
    output = capsys.readouterr().out
    assert "SYNTHETIC — NOT REAL DATA" in output and "SYN-WAV-0016 v2: G1 block" in output and "reopened 2 of" in output
    assert "Crítica" in output and "SYN-WAV-0019 v1: G1 block" in output
    validator = Draft202012Validator(load(ROOT / "schemas" / "prediction.schema.json"), format_checker=FormatChecker())
    prediction = load(tmp_path / "SYN-WAV-0016" / "v2" / "prediction.json")
    assert not list(validator.iter_errors(prediction))
    assert prediction["gate"]["recommendation"] == "block" and len(prediction["fields"]) == 66
    assert set(prediction["reopened_validations"]) == {"signature.date", "z_end.suite_or_room"}
    check("validation.schema.json", load(tmp_path / "SYN-WAV-0016" / "v2" / "validation.json"))
    assert cli.main(["--run", str(tmp_path / "nothing")]) == 2


def test_every_rule_action_and_role_has_text_in_both_languages():
    config = finding_rules()
    rules = config["finding_rules"] + [config["product_undetermined"]]
    actions = {r["action"] for r in rules} | {config["stale_source_action"]}
    entries = [config["owners"]["default"], *config["owners"]["by_group"].values(), *config["owners"]["by_field"].values()]
    roles = {e[k] for e in entries for k in ("internal_owner", "resolving_party")}
    roles |= {"customer_technical_contact_a_end", "customer_technical_contact_z_end"}
    params = {"field": "x", "count": 2, "documents": "d.pdf", "version": 2}
    for language in LANGUAGES:
        for rule in rules:
            assert t(f"finding_rule.{rule['rule_id']}", language, **params)
        for action in actions:
            assert t(f"finding_action.{action}", language, **params)
        for role in roles:
            assert t(f"owner_role.{role}", language)
    with pytest.raises(KeyError):
        t("finding_rule.NOPE")


def test_validator_code_has_no_user_facing_sentences():
    """Finding text lives in locales/: the validator modules only hold keys."""
    texts = [v for area in ("finding_rule", "finding_action", "owner_role") for v in load(ROOT / "locales" / "en.json")[area].values()
             if v != "Customer"]  # the word also appears in comments
    for path in (ROOT / "src" / "validators").glob("*.py"):
        if path.name == "cli.py":
            continue
        source = path.read_text(encoding="utf-8")
        assert not [x for x in texts if x in source], path.name


def test_finding_rules_are_complete_and_ordered():
    config = finding_rules()
    assert [r["rule_id"] for r in config["finding_rules"]][-2:] == ["G1-REQUIRED", "G1-CONSISTENCY"]
    assert all(set(r["when"]["status"]) <= {"missing", "contradictory"} for r in config["finding_rules"])
    groups = {r["group"] for p in ("EPL", "WAVELENGTH") for r in product_rules(p).values()}
    assert groups <= set(config["owners"]["by_group"])
    base_keys = {r.get("base_key", k) for p in ("EPL", "WAVELENGTH") for k, r in product_rules(p).items()}
    assert set(config["owners"]["by_field"]) <= base_keys
    assert set(config["due_in_business_days"]) == set(severity_rank())
