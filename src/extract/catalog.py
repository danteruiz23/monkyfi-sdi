"""Field catalog from rules/fields.*.json, with endpoint fields expanded per end (a_end., z_end.)."""

from __future__ import annotations

import json
from functools import lru_cache

from .. import RULES_DIR

PRODUCT_FILES = {"EPL": "fields.epl.json", "WAVELENGTH": "fields.wavelength.json"}
ENDS = ("a_end", "z_end")
END_NAME = {"a_end": "A end", "z_end": "Z end"}


def _load(name: str) -> dict:
    return json.loads((RULES_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def rules_version() -> str:
    parts = [f"{n}@{_load(n)['rules_version']}" for n in
             ("fields.common.json", *PRODUCT_FILES.values(), "synonyms.json", "extraction.json")]
    return ";".join(parts)


@lru_cache(maxsize=None)
def extraction_rules() -> dict:
    return _load("extraction.json")


@lru_cache(maxsize=None)
def synonyms() -> dict[str, list[str]]:
    return _load("synonyms.json")["field_label_synonyms"]


def _expand(rule: dict, product: str | None) -> list[dict]:
    if rule["scope"] != "endpoint":
        return [dict(rule, products=[product] if product else ["EPL", "WAVELENGTH"])]
    return [dict(rule, key=f"{end}.{rule['key']}", base_key=rule["key"], end=end,
                 products=[product] if product else ["EPL", "WAVELENGTH"]) for end in ENDS]


@lru_cache(maxsize=None)
def product_rules(product: str) -> dict[str, dict]:
    """{field_key: rule} for one product, in rules-file order."""
    if product not in PRODUCT_FILES:
        raise ValueError(f"unknown product {product!r}")
    rules: dict[str, dict] = {}
    for rule in _load("fields.common.json")["fields"]:
        for r in _expand(rule, None):
            rules[r["key"]] = r
    for rule in _load(PRODUCT_FILES[product])["fields"]:
        for r in _expand(rule, product):
            rules[r["key"]] = r
    return rules


@lru_cache(maxsize=None)
def common_rules() -> dict[str, dict]:
    return {k: r for k, r in product_rules("EPL").items() if r["products"] == ["EPL", "WAVELENGTH"]}


def union_rules() -> dict[str, dict]:
    """Every field of every product. The model sees this catalog because the product is only known
    after extraction; the product's own list is applied afterwards."""
    merged: dict[str, dict] = {}
    for product in PRODUCT_FILES:
        for key, rule in product_rules(product).items():
            if key in merged and merged[key]["products"] != rule["products"]:
                merged[key] = dict(merged[key], products=sorted(set(merged[key]["products"]) | set(rule["products"])))
            else:
                merged.setdefault(key, rule)
    return merged


def describe(rule: dict) -> str:
    """One catalog line for the prompt."""
    words = rule.get("base_key", rule["key"]).replace("_", " ").replace(".", " — ")
    parts = [f"{rule['key']}: {words}"]
    if rule.get("end"):
        parts.append(f"at the {END_NAME[rule['end']]} only")
    parts.append(f"type {rule['value_type']}")
    if rule.get("enum"):
        parts.append("one of " + " / ".join(rule["enum"]))
    if rule.get("examples"):
        parts.append("e.g. " + ", ".join(rule["examples"]))
    if rule.get("condition"):
        parts.append(f"conditional: {rule['condition']}")
    labels = synonyms().get(rule.get("base_key", rule["key"]))
    if labels:
        parts.append("may be labeled " + ", ".join(f'"{s}"' for s in labels))
    if len(rule["products"]) == 1:
        parts.append(f"{rule['products'][0]} only")
    return "; ".join(parts)
