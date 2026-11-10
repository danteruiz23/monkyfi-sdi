"""Phase 4, UC07 minimal slice: a shared resource (for example one cross-connect request for several
orders) is one record linked to every affected order; when it is blocked, every linked order is flagged,
with one shared action instead of one request per order. Deterministic; rules in rules/shared_resources.json.
"""

from __future__ import annotations

import json
import re
from datetime import date
from functools import lru_cache

from .. import RULES_DIR
from ..ingest.documents import Document
from ..validators.findings import add_business_days
from .dates import _has_cue, _sentences
from .dependencies import sent_on


@lru_cache(maxsize=None)
def shared_rules() -> dict:
    return json.loads((RULES_DIR / "shared_resources.json").read_text(encoding="utf-8"))


def resource_mentions(order_id: str, documents: list[Document] | None) -> list[dict]:
    """Every reference to a shared resource in one order's emails, with the orders named next to it."""
    if not documents:
        return []
    rules = shared_rules()
    order_pattern = re.compile(rules["order_id_pattern"])
    out = []
    for document in documents:
        if document.doc_type != "email":
            continue
        text = "\n".join(p.text for p in document.pages)
        sentences = [s for p in document.pages for s in _sentences(p.text)]
        for kind, config in rules["kinds"].items():
            for reference in sorted(set(re.findall(config["reference_pattern"], text))):
                blocked = next((s for s in sentences if _has_cue(s, rules["blocked_cues"])), None)
                cleared = next((s for s in sentences if _has_cue(s, rules["cleared_cues"])), None)
                state = "blocked" if blocked else "cleared" if cleared else "unknown"
                where = next((s for s in sentences if reference in s), None)
                out.append({"reference": reference, "kind": kind, "order_id": order_id,
                            "named_orders": sorted(set(order_pattern.findall(text)) | {order_id}),
                            "doc_id": document.filename, "page": 1, "sent_on": (sent_on(document) or date.min).isoformat(),
                            "state": state, "evidence": {"reference_sentence": where, "state_sentence": blocked or cleared}})
    return out


def link_resources(mentions: list[dict], as_of: date) -> dict[str, dict]:
    """One record per reference across the run: linked orders, state from the latest email, one action."""
    rules = shared_rules()
    records: dict[str, dict] = {}
    for reference in sorted({m["reference"] for m in mentions}):
        found = sorted((m for m in mentions if m["reference"] == reference), key=lambda m: (m["sent_on"], m["order_id"]))
        latest_on = found[-1]["sent_on"]
        latest = [m for m in found if m["sent_on"] == latest_on]
        states = {m["state"] for m in latest}
        state = "blocked" if "blocked" in states else "cleared" if states == {"cleared"} else "unknown"
        kind = found[0]["kind"]
        config = rules["kinds"][kind]
        linked = sorted({o for m in found for o in m["named_orders"]} | {m["order_id"] for m in found})
        action = None
        if state != "cleared":
            action = {"action_id": f"SR-{reference}", "action": rules["action"]["action"], "shared_resource": reference,
                      "owner": config["owner"], "status": "open", "shared": True, "linked_order_ids": linked,
                      "due_date": add_business_days(as_of, rules["action"]["due_in_business_days"]).isoformat(),
                      "reason": state, "decision": "UC07"}
        records[reference] = {
            "shared_resource_id": reference, "kind": kind, "is_blocked": state == "blocked", "state": state,
            "linked_order_ids": linked, "milestone": config["milestone"], "owner": config["owner"],
            "seen_in": [{"order_id": m["order_id"], "doc_id": m["doc_id"], "sent_on": m["sent_on"], "state": m["state"],
                         "evidence": m["evidence"]} for m in found],
            "action": action,
        }
    return records


def attach_to_plan(plan: dict, order_id: str, records: dict[str, dict], run_orders: set[str]) -> dict:
    """Flags every shared resource linked to this order on its plan; a blocked one blocks the milestone."""
    linked = [r for r in records.values() if order_id in r["linked_order_ids"]]
    plan["shared_resources"] = [dict({k: v for k, v in r.items() if k != "action"},
                                     action_id=r["action"]["action_id"] if r["action"] else None,
                                     linked_not_in_run=sorted(set(r["linked_order_ids"]) - run_orders))
                                for r in linked]
    for r in linked:
        if r["action"] and not any(a["action_id"] == r["action"]["action_id"] for a in plan["actions"]):
            plan["actions"].append(dict(r["action"]))
        for m in plan["milestones"]:
            if m["key"] == r["milestone"] and r["is_blocked"]:
                m["state"] = "blocked"
                m["blocked_by"] = sorted(set(m["blocked_by"]) | {r["shared_resource_id"]})
    return plan
