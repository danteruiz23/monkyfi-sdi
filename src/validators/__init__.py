"""Validators and gate G1 (SPEC 6, 8.3, UC02, UC03). Deterministic: no model takes part.

- findings.py — one finding per missing or contradictory G1 field, with severity, sources, owner,
  due date and action (rules/findings.json, rules/fields.*.json).
- gate.py — the G1 recommendation (rules/gates.json, D28) and the human override.
- versions.py — what a new order version changed and which validations it reopens.
- evaluate.py — the validation record for one order version and its projection for the evals.
"""

from .evaluate import add_to_prediction, render_finding, validate_version
from .findings import lower_severity, validate
from .gate import evaluate_g1, override_gate
from .versions import carry_verifications, compare_versions

__all__ = ["add_to_prediction", "carry_verifications", "compare_versions", "evaluate_g1", "lower_severity",
           "override_gate", "render_finding", "validate", "validate_version"]
