"""Validator rules from rules/*.json: finding rules, owners, due dates, severity levels and gates."""

from __future__ import annotations

import json
from functools import lru_cache

from .. import RULES_DIR

VALIDATOR_VERSION = "0.1.0"
RULE_FILES = ("findings.json", "gates.json", "severity.json")


@lru_cache(maxsize=None)
def load(name: str) -> dict:
    return json.loads((RULES_DIR / name).read_text(encoding="utf-8"))


def finding_rules() -> dict:
    return load("findings.json")


def gate_rule(gate: str) -> dict:
    return load("gates.json")["gates"][gate]


@lru_cache(maxsize=None)
def severity_rank() -> dict[str, int]:
    return {level["level"]: level["rank"] for level in load("severity.json")["levels"]}


def higher(a: str, b: str | None) -> str:
    """The higher of two severities (tie-break rule, D20)."""
    rank = severity_rank()
    return a if b is None or rank[a] >= rank[b] else b


@lru_cache(maxsize=None)
def rules_version() -> str:
    return ";".join(f"{name}@{load(name)['rules_version']}" for name in RULE_FILES)
