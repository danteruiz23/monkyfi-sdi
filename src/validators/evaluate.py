"""Validation of one order version: findings, the G1 recommendation and, when a previous version
exists, what the new version reopened. Returns a validation record (schemas/validation.schema.json)
and projects it onto the eval runner's prediction format."""

from __future__ import annotations

from datetime import date

from ..extract.prediction import check
from ..i18n import DEFAULT_LANGUAGE, t
from .findings import validate
from .gate import evaluate_g1
from .rules import VALIDATOR_VERSION, rules_version
from .versions import compare_versions, finding_changes


def validate_version(extraction: dict, *, as_of: date, evaluated_at: str, previous: dict | None = None,
                     previous_validation: dict | None = None, documents=None, customers: list[str] | None = None) -> dict:
    findings = validate(extraction, as_of, documents, customers)
    warnings = []
    if documents is None or customers is None:
        warnings.append("customer scoping was not run: the package documents or the customer register were not given")
    change = None
    if previous is not None:
        change = compare_versions(previous, extraction)
        if previous_validation is not None:
            change["previous_gate_recommendation"] = previous_validation["gate"]["recommendation"]
            change["findings"] = finding_changes(previous_validation["findings"], findings)
        reopened = set(change["reopened_validations"])
        for finding in findings:
            finding["reopened"] = finding["field_key"] in reopened
    elif extraction["version_no"] > 1:
        warnings.append("no previous version was available; the version comparison was not run")
    record = {
        "synthetic": True,
        "order_dir_id": extraction["order_dir_id"], "version_no": extraction["version_no"],
        "product": extraction["product"],
        "run": {"validator_version": VALIDATOR_VERSION, "rules_version": rules_version(),
                "extraction_rules_version": extraction["run"]["rules_version"],
                "extraction_model": f"{extraction['run']['provider']}/{extraction['run']['model']}",
                "extraction_prompt_version": extraction["run"]["prompt_version"],
                "as_of": as_of.isoformat(), "evaluated_at": evaluated_at,
                "customer_scoping": documents is not None and customers is not None},
        "findings": findings,
        "gate": evaluate_g1(findings, evaluated_at),
        "version_change": change,
        "approvals": [],
        "warnings": warnings,
    }
    check("validation.schema.json", record)
    return record


def add_to_prediction(prediction: dict, validation: dict) -> dict:
    """The sections the eval runner scores from Phase 3: findings, gate and reopened validations."""
    out = dict(prediction)
    out["findings"] = [{"field_key": f["field_key"], "rule_id": f["rule_id"], "severity": f["severity"],
                        "escalated": f["escalated"]} for f in validation["findings"]]
    out["gate"] = {"gate": "G1", "recommendation": validation["gate"]["recommendation"]}
    if validation["version_change"] is not None:
        out["reopened_validations"] = list(validation["version_change"]["reopened_validations"])
    check("prediction.schema.json", out)
    return out


def render_finding(finding: dict, language: str = DEFAULT_LANGUAGE) -> dict:
    """A finding's user-facing text in one language, from locales/."""
    return {"finding_id": finding["finding_id"], "field_key": finding["field_key"],
            "severity": t(f"severity.{finding['severity']}", language),
            "description": t(finding["description"]["key"], language, **finding["description"]["params"]),
            "action": t(finding["action"]["key"], language, **finding["action"]["params"]),
            "owner": t(f"owner_role.{finding['owner']}", language),
            "resolving_party": t(f"owner_role.{finding['resolving_party']}", language),
            "impact": t(f"impact.{finding['impact']}", language),
            "status": t(f"finding_status.{finding['status']}", language),
            "due_date": finding["due_date"]}
