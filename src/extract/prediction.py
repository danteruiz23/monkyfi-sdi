"""Projection of an extraction record onto the eval runner's prediction format, plus schema checks.

Only the "fields" section is produced in Phase 2; findings, gate and dates are later phases and are
left out so the runner reports them as not run. Sources are identified by file name; the runner
maps file names to the golden labels' document ids.
"""

from __future__ import annotations

import json
from functools import lru_cache

from jsonschema import Draft202012Validator

from .. import SCHEMAS_DIR


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8")))


def check(name: str, document: dict) -> None:
    errors = sorted(_validator(name).iter_errors(document), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors[:5])
        raise ValueError(f"{name}: {detail}")


def to_prediction(extraction: dict) -> dict:
    fields = []
    for f in extraction["fields"]:
        source = f["source"] or {}
        fields.append({"field_key": f["field_key"], "status": f["status"], "raw_value": f["raw_value"],
                       "normalized_value": f["normalized_value"], "source_doc_id": source.get("filename"),
                       "source_page": source.get("page"), "source_location": source.get("location")})
    prediction = {"external_order_id": extraction["order_dir_id"], "version_no": extraction["version_no"],
                  "fields": fields}
    check("prediction.schema.json", prediction)
    return prediction
