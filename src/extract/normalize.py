"""Deterministic normalization by value type (SPEC 8.2: raw_value and normalized_value).

Must agree with the golden labels' convention (data/synthetic/generate.py); a test checks every
golden raw value. Unrecognized input raises ValueError: a value is never guessed.
"""

from __future__ import annotations

import re
import string
from datetime import date, datetime

from ..ingest.documents import squash
from .catalog import extraction_rules

DATE_FORMATS = ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y")
_SPEED = re.compile(r"^(\d+(?:\.\d+)?)\s*([GM])(?:b(?:it)?(?:ps|/s)|bps)?\b", re.I)
_TRUE = ("yes", "true", "required")
_FALSE = ("no", "false", "not required")


def parse_date(raw: str) -> date:
    text = squash(raw)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognized date: {raw!r}")


def normalize(value_type: str, raw: str):
    text = squash(raw)
    if not text:
        raise ValueError("empty value")
    if value_type == "speed":
        m = _SPEED.match(text)
        if not m:
            raise ValueError(f"unrecognized speed: {raw!r}")
        mbps = float(m.group(1)) * (1000 if m.group(2).upper() == "G" else 1)
        if mbps != int(mbps):
            raise ValueError(f"speed is not a whole number of Mbps: {raw!r}")
        return {"value": int(mbps), "unit": "Mbps"}
    if value_type == "date":
        return parse_date(text).isoformat()
    if value_type == "boolean":
        lowered = text.lower()
        if lowered in _TRUE:
            return True
        if lowered in _FALSE:
            return False
        raise ValueError(f"unrecognized yes/no value: {raw!r}")
    if value_type == "integer":
        digits = re.sub(r"[,\s]", "", text)
        if not digits.isdigit():
            raise ValueError(f"unrecognized integer: {raw!r}")
        return int(digits)
    if value_type == "list":
        return [item.strip() for item in text.split(",") if item.strip()]
    if value_type == "enum":
        return text.lower()
    return text


def placeholder_kind(raw: str) -> str | None:
    """'not_applicable' or 'awaited' when the printed text is a placeholder, not a value."""
    text = squash(raw).lower().strip(string.punctuation + " ")
    for kind, words in extraction_rules()["placeholders"].items():
        if text in words:
            return kind
    return None
