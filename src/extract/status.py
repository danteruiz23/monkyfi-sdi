"""The six field_value statuses (SPEC 8.2) and who may set each one.

Extraction sets only pending, missing, not_applicable and contradictory. verified belongs to the
data owner (D28) and needs a named human; stale marks a value superseded by a newer order version.
Neither changes the value or its source, and neither is ever set by a model.
"""

from __future__ import annotations

import copy

STATUSES = ("verified", "pending", "missing", "not_applicable", "contradictory", "stale")
EXTRACTION_STATUSES = ("pending", "missing", "not_applicable", "contradictory")


def mark_verified(field_value: dict, verified_by: str, verified_at: str) -> dict:
    """A data owner confirms a value. Only a consistent value with a source can be verified."""
    if not verified_by or not verified_by.strip():
        raise ValueError("verified needs the name of the human who verified the value")
    if field_value["status"] != "pending" or field_value.get("normalized_value") is None or not field_value.get("source"):
        raise ValueError(f"only a pending value with a source can be verified (status is {field_value['status']})")
    out = copy.deepcopy(field_value)
    out.update(status="verified", verified_by=verified_by.strip(), verified_at=verified_at)
    return out


def mark_stale(field_value: dict, superseded_by_version: int) -> dict:
    """A newer order version superseded this value. The value and its source are kept for history."""
    if field_value["status"] == "stale":
        return copy.deepcopy(field_value)
    out = copy.deepcopy(field_value)
    out.update(status="stale", previous_status=field_value["status"], superseded_by_version=superseded_by_version)
    return out
