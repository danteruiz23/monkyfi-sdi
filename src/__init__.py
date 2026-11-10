"""Monkyfi Service Delivery Intelligence (SPEC 7). Run modules from the repo root, e.g.
`.venv/bin/python -m src.extract.cli --help`."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "rules"
PROMPTS_DIR = ROOT / "prompts"
SCHEMAS_DIR = ROOT / "schemas"
