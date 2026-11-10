"""Shared test helpers. Run from the repo root:  .venv/bin/python -m pytest -q"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic"
MARK = "SYNTHETIC — NOT REAL DATA"

sys.path.insert(0, str(DATA))
sys.path.insert(0, str(ROOT / "evals"))


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


MANIFEST = load(DATA / "manifest.json")
VERSION_DIRS = sorted(p.parent for p in (DATA / "orders").glob("*/v*/golden.json"))
GOLDENS = {d: load(d / "golden.json") for d in VERSION_DIRS}


def version_id(path: Path) -> str:
    return f"{path.parent.name}-{path.name}"
