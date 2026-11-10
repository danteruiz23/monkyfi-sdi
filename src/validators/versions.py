"""Comparison of an order version with the previous one (UC03).

A validation is reopened only when its field's current value differs from the previous version's.
The current value of a field is what the documents issued for this version print; a document
carried over from an earlier version does not make a field "changed" (that mismatch is its own
finding). Unchanged fields keep a human's `verified`; changed fields lose it, and the previous
value is kept as `stale`. Which changes may move milestones is flagged here; the plan is Phase 4.
"""

from __future__ import annotations

import copy
import json

from ..extract.catalog import product_rules
from ..extract.status import mark_stale
from .rules import finding_rules


def current_values(field: dict) -> dict[str, str]:
    """{comparable value: raw text} printed for a field, preferring documents of the current version."""
    sources = [s for s in field["sources"] if not s.get("placeholder")]
    fresh = [s for s in sources if not s["stale_source"]] or sources
    return {json.dumps(s["normalized_value"], sort_keys=True, ensure_ascii=False)
            if s["normalized_value"] is not None else f"raw:{s['raw_value']}": s["raw_value"] for s in fresh}


def compare_versions(previous: dict, current: dict) -> dict:
    """What changed from `previous` to `current` (two extraction records of the same order)."""
    if previous["order_dir_id"] != current["order_dir_id"]:
        raise ValueError("the two records are not versions of the same order")
    if previous["version_no"] >= current["version_no"]:
        raise ValueError("the previous record must be an earlier version")
    config = finding_rules()["version_change"]
    catalog = product_rules(current["product"]) if current["product"] else {}
    before = {f["field_key"]: f for f in previous["fields"]}
    changed, superseded = [], []
    for field in current["fields"]:
        key = field["field_key"]
        if key in config["ignored_fields"]:
            continue
        old = before.get(key)
        old_values = current_values(old) if old else {}
        new_values = current_values(field)
        # With no printed value on either side, the status is what can change (e.g. missing → not applicable).
        if (set(old_values) or {old["status"] if old else None}) == (set(new_values) or {field["status"]}):
            continue
        rule = catalog[key]
        affects_plan = (rule["group"] in config["plan_affecting"]["groups"]
                        or rule.get("base_key", key) in config["plan_affecting"]["fields"])
        changed.append({"field_key": key, "group": rule["group"], "previous": sorted(old_values.values()),
                        "current": sorted(new_values.values()), "previous_status": old["status"] if old else None,
                        "current_status": field["status"], "plan_impact": affects_plan})
        if old and old["raw_value"] is not None:
            superseded.append(mark_stale(old, current["version_no"]))
    return {
        "previous_version_no": previous["version_no"],
        "changed_fields": changed,
        "reopened_validations": [c["field_key"] for c in changed],
        "unchanged_validations": len(current["fields"]) - len(changed),
        "plan_impact": any(c["plan_impact"] for c in changed),
        "plan_impact_fields": [c["field_key"] for c in changed if c["plan_impact"]],
        "superseded_values": superseded,
    }


def carry_verifications(previous_fields: list[dict], current_fields: list[dict], reopened: list[str]) -> list[dict]:
    """Current fields, keeping a human's `verified` where the validation was not reopened and the
    value is the same. Never verifies anything a human did not verify."""
    verified = {f["field_key"]: f for f in previous_fields if f["status"] == "verified"}
    out = []
    for field in current_fields:
        old = verified.get(field["field_key"])
        field = copy.deepcopy(field)
        if (old and field["field_key"] not in reopened and field["status"] == "pending"
                and field["normalized_value"] == old["normalized_value"]):
            field.update(status="verified", verified_by=old["verified_by"], verified_at=old["verified_at"])
        out.append(field)
    return out


def finding_changes(previous_findings: list[dict], current_findings: list[dict]) -> dict:
    """Findings by (rule, field): new in this version, carried over, or no longer raised."""
    def ident(f):
        return f"{f['rule_id']}:{f['field_key']}"
    old, new = {ident(f) for f in previous_findings}, {ident(f) for f in current_findings}
    return {"new": sorted(new - old), "carried_over": sorted(new & old), "no_longer_raised": sorted(old - new)}
