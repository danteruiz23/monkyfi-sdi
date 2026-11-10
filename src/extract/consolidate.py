"""Field status across the documents of one order version. Deterministic (SPEC 7.1, 8, 8.4).

For each critical field of the product:
- Only documents of a type in rules/extraction.json field_source_doc_types count as sources.
- Printed values that normalize to the same thing → pending, with the value taken from the
  field's authoritative document when it has one. Values that disagree → contradictory, with no
  value and every conflicting source kept.
- Only "Not applicable" printed → not_applicable. Only "To be confirmed" (or similar) → pending
  with no value: the value is awaited, not missing.
- Nothing printed: a conditional field whose condition is false → not_applicable; otherwise →
  missing. A condition that cannot be evaluated counts as holding (the conservative reading).
"""

from __future__ import annotations

import json

from .catalog import extraction_rules, product_rules
from .ground import Mention
from .normalize import normalize, placeholder_kind


def _comparable(normalized) -> str:
    return json.dumps(normalized, sort_keys=True, ensure_ascii=False)


def _source(m: Mention, normalized=None, kind=None, stale=False, error=None) -> dict:
    out = {"filename": m.filename, "doc_type": m.doc_type, "page": m.page, "location": m.location,
           "raw_value": m.raw_value, "normalized_value": normalized, "placeholder": kind, "stale_source": stale}
    if error:
        out["normalization_error"] = error
    if m.notes:
        out["notes"] = list(m.notes)
    return out


def _ref(m: Mention) -> dict:
    return {"filename": m.filename, "doc_type": m.doc_type, "page": m.page, "location": m.location}


def document_versions(mentions: list[Mention]) -> dict[str, int]:
    """Version printed in each document's header, from its order_version mentions."""
    versions: dict[str, int] = {}
    for m in mentions:
        if m.field_key == "order_version" and m.raw_value.strip().isdigit():
            if "header" in m.location.lower() or m.filename not in versions:
                versions[m.filename] = int(m.raw_value)
    return versions


def detect_product(mentions: list[Mention]) -> str | None:
    sources = set(extraction_rules()["field_source_doc_types"])
    values = {placeholder_kind(m.raw_value) or m.raw_value.strip().upper()
              for m in mentions if m.field_key == "product" and m.doc_type in sources}
    if len(values) == 1 and next(iter(values)) in ("EPL", "WAVELENGTH"):
        return next(iter(values))
    return None


def _state(rule: dict, mentions: list[Mention], doc_versions: dict[str, int], current_version: int | None) -> dict:
    values, placeholders, sources = [], [], []
    for m in mentions:
        stale = current_version is not None and doc_versions.get(m.filename, current_version) < current_version
        kind = placeholder_kind(m.raw_value)
        if kind:
            placeholders.append((m, kind))
            sources.append(_source(m, kind=kind, stale=stale))
            continue
        try:
            normalized, error = normalize(rule["value_type"], m.raw_value), None
        except ValueError as exc:
            normalized, error = None, str(exc)
        values.append((m, normalized, error))
        sources.append(_source(m, normalized, stale=stale, error=error))

    base = {"field_key": rule["key"], "raw_value": None, "normalized_value": None, "source": None,
            "sources": sources, "extracted_by": "model", "notes": []}
    if values:
        distinct = {_comparable(n) if e is None else f"raw:{m.raw_value}" for m, n, e in values}
        if len(distinct) > 1:
            return dict(base, status="contradictory",
                        notes=[f"{len(distinct)} different values across {len({m.filename for m, _, _ in values})} "
                               "document(s)"])
        chosen = next((v for v in values if v[0].doc_type == rule["authoritative_source"]), values[0])
        m, normalized, error = chosen
        notes = [f"value could not be normalized: {error}"] if error else []
        if any(s["stale_source"] for s in sources):
            notes.append("a source document is from an earlier order version")
        return dict(base, status="pending", raw_value=m.raw_value, normalized_value=normalized, source=_ref(m),
                    notes=notes)
    if any(kind == "not_applicable" for _, kind in placeholders):
        m = next(m for m, kind in placeholders if kind == "not_applicable")
        return dict(base, status="not_applicable", source=_ref(m), notes=["printed as not applicable"])
    if placeholders:
        m = placeholders[0][0]
        return dict(base, status="pending", source=_ref(m), notes=[f"value awaited: printed as {m.raw_value!r}"])
    return dict(base, status=None)


def _condition(rule: dict, states: dict[str, dict]) -> bool | None:
    """True / False when the applies_when condition can be evaluated; None when it cannot."""
    cond = rule.get("applies_when")
    if not cond:
        return None
    driver_key = f"{rule['end']}.{cond['field']}" if rule.get("end") else cond["field"]
    driver = states.get(driver_key)
    if driver is None or driver["status"] in (None, "missing", "contradictory"):
        return None
    if driver["status"] == "not_applicable":
        return False
    value = driver["normalized_value"]
    if "present" in cond:
        return (value is not None) == bool(cond["present"])
    if value is None:
        return None
    if isinstance(value, bool):
        return value == (cond["equals"].lower() in ("yes", "true"))
    return str(value).lower() == cond["equals"].lower()


def consolidate(mentions: list[Mention], product: str, current_version: int | None = None) -> list[dict]:
    rules = product_rules(product)
    allowed = set(extraction_rules()["field_source_doc_types"])
    usable = [m for m in mentions if m.doc_type in allowed]
    versions = document_versions(usable)
    by_key: dict[str, list[Mention]] = {}
    for m in usable:
        by_key.setdefault(m.field_key, []).append(m)

    states = {key: _state(rule, by_key.get(key, []), versions, current_version) for key, rule in rules.items()}
    for key, rule in rules.items():
        state = states[key]
        if state["status"] is not None:
            continue
        state["extracted_by"] = "rule"
        if rule["requirement"] == "conditional":
            holds = _condition(rule, states)
            if holds is False:
                state.update(status="not_applicable", notes=[f"not printed; condition does not hold: {rule['condition']}"])
                continue
            if holds is None and rule.get("applies_when"):
                state["notes"] = ["not printed; its condition could not be evaluated, so it is treated as required"]
            elif holds is None:
                state["notes"] = ["not printed; whether it applies is not stated, so it is treated as required"]
        state.update(status="missing")
        state["notes"] = state["notes"] or ["not printed in any source document"]
    return [states[key] for key in rules]
