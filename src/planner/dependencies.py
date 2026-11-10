"""Phase 4: supplier dependencies, follow-up and the dependency graph (UC05, RF04, D26, D55).

Deterministic. One supplier dependency per registered supplier that wrote in the package. Its date and the
date's type come from the typed email dates (src/planner/dates.py); a supplier's firm date stays on the
dependency (D26). Without a firm commitment a follow-up is scheduled from the supplier's last email, using
the supplier's thresholds (D55). A missing date makes the supplier input "missing" and the delay "unknown",
never "delayed" (UC05, D62).
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from functools import lru_cache

from .. import RULES_DIR
from ..ingest.documents import Document
from ..validators.findings import add_business_days

_SENT = re.compile(r"^Sent:\s*(\d{4}-\d{2}-\d{2})", re.M)
_SUBJECT = re.compile(r"^Subject:\s*(.+)$", re.M)


@lru_cache(maxsize=None)
def dependency_rules() -> dict:
    return json.loads((RULES_DIR / "dependencies.json").read_text(encoding="utf-8"))


def sent_on(document: Document) -> date | None:
    match = _SENT.search(document.pages[0].text)
    return datetime.strptime(match.group(1), "%Y-%m-%d").date() if match else None


def subject_of(document: Document) -> str | None:
    match = _SUBJECT.search(document.pages[0].text)
    return re.sub(r"^(?:RE|FW|FWD):\s*", "", match.group(1).strip(), flags=re.I) if match else None


def supplier_dependencies(dates: dict, documents: list[Document] | None, register: list[dict],
                          as_of: date) -> list[dict]:
    """One dependency per registered supplier that wrote in the package."""
    if not documents:
        return []
    rules = dependency_rules()["supplier_follow_up"]
    by_name = {s["name"]: s for s in register}
    by_file = {d.filename: d for d in documents}
    out = []
    suppliers = sorted({e["supplier"] for e in dates.get("supplier_emails", [])})
    for name in suppliers:
        emails = sorted((by_file[e["doc_id"]] for e in dates["supplier_emails"] if e["supplier"] == name),
                        key=lambda d: (sent_on(d) or date.min, d.filename))
        latest = emails[-1]
        files = {d.filename for d in emails}
        said = [m for m in dates["mentions"] if m["doc_id"] in files and m.get("sender_supplier") == name
                and m["type"] in ("forecast", "committed")]
        firm = [m for m in said if m["type"] == "committed" and m["scope"] == "supplier_dependency"]
        tentative = [m for m in said if m["type"] == "forecast"]
        chosen = None
        if len({m["date"] for m in firm}) == 1:
            chosen = firm[-1]
        elif not firm and len({m["date"] for m in tentative}) == 1:
            chosen = tentative[-1]
        conflicting = bool(said) and chosen is None
        supplier = by_name.get(name, {})
        first = supplier.get("follow_up_threshold_days", rules["default_first_follow_up_business_days"])
        escalate = supplier.get("escalation_threshold_days", rules["default_escalation_business_days"])
        follow_up_expected = chosen is None or chosen["type"] != "committed"
        anchor = sent_on(latest)
        follow_up = None
        if follow_up_expected:
            if anchor is None:
                follow_up = {"anchor": None, "first_follow_up_on": None, "escalation_on": None,
                             "state": "anchor_unknown", "owner": rules["owner"], "escalate_to": rules["escalate_to"]}
            else:
                first_on, escalate_on = add_business_days(anchor, first), add_business_days(anchor, escalate)
                state = ("escalation_due" if as_of >= escalate_on else
                         "follow_up_due" if as_of >= first_on else "not_due")
                follow_up = {"anchor": anchor.isoformat(), "anchor_doc_id": latest.filename,
                             "first_follow_up_on": first_on.isoformat(), "escalation_on": escalate_on.isoformat(),
                             "thresholds_business_days": [first, escalate], "state": state,
                             "owner": rules["owner"], "escalate_to": rules["escalate_to"]}
        out.append({
            "dependency_id": f"D{len(out) + 1}", "kind": "supplier", "supplier": name,
            "source_doc_id": latest.filename, "description": subject_of(latest),
            "supplier_date": chosen["date"] if chosen else None,
            "supplier_date_type": chosen["type"] if chosen else None,
            "supplier_date_evidence": ({"doc_id": chosen["doc_id"], "page": chosen["page"],
                                        "sentence": chosen.get("sentence")} if chosen else None),
            "assumptions": list(chosen.get("assumptions") or []) if chosen else [],
            "conflicting_supplier_dates": sorted({m["date"] for m in said}) if conflicting else [],
            # Whether the supplier has given its input (a date). Not a delivery forecast (D62).
            "supplier_input": "complete" if chosen else "missing",
            # Missing information is never a delay (UC05).
            "delay_assessment": "unknown" if chosen is None else "not_assessed",
            "follow_up_expected": follow_up_expected,
            "follow_up": follow_up,
        })
    return out


def dependency_graph(milestones: list[dict], dependencies: list[dict]) -> dict:
    """Nodes are milestones and external dependencies; edges point from what must finish first."""
    keys = {m["key"] for m in milestones}
    edges = [{"from": p, "to": m["key"], "kind": "milestone"} for m in milestones for p in m["predecessors"]
             if p in keys]
    supplier_milestone = next((m["key"] for m in milestones if m["key"] in ("third_party_access",
                                                                             "supplier_segments_foc")), None)
    for d in dependencies:
        if supplier_milestone:
            edges.append({"from": d["dependency_id"], "to": supplier_milestone, "kind": "supplier"})
    nodes = [{"id": m["key"], "kind": "milestone"} for m in milestones] + [
        {"id": d["dependency_id"], "kind": d["kind"], "supplier": d.get("supplier")} for d in dependencies]
    return {"nodes": nodes, "edges": edges}
