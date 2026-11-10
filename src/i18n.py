"""User-facing text from locales/ (SPEC 7.4). No user-facing string is written in code: code holds
a key and its parameters, and the text is rendered here in the reader's language."""

from __future__ import annotations

import json
from functools import lru_cache

from . import ROOT

LOCALES_DIR = ROOT / "locales"
DEFAULT_LANGUAGE = "en"
LANGUAGES = ("en", "es")


@lru_cache(maxsize=None)
def _locale(language: str) -> dict:
    if language not in LANGUAGES:
        raise ValueError(f"unknown language {language!r}")
    return json.loads((LOCALES_DIR / f"{language}.json").read_text(encoding="utf-8"))


def t(key: str, language: str = DEFAULT_LANGUAGE, **params) -> str:
    """Text for a dotted key (the last part may itself contain dots or dashes). A missing key is an error."""
    node = _locale(language)
    area, _, name = key.partition(".")
    try:
        text = node[area][name]
    except (KeyError, TypeError):
        raise KeyError(f"locales/{language}.json has no key {key!r}") from None
    return text.format(**params) if params else text
