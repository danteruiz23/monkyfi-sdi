"""Synthetic order generator.

SYNTHETIC — NOT REAL DATA. Every company, person, address and identifier
produced here is fictional.

Each order starts from a "truth" (the correct value of every critical field).
Defects are seeded on purpose, so the golden label is known by construction:
the generator writes the documents and the expected answers from the same spec.

Output (all under data/synthetic/):
    orders/<order id>/v<N>/documents/*.pdf  the order package for that version (document of record)
    orders/<order id>/v<N>/markdown/*.md    the same documents as Markdown, for review and diffs
    orders/<order id>/v<N>/golden.json      the expected answers for that version
    events/*.json                           simulated event files
    manifest.json                           index of orders, splits and mandatory cases

Usage (from the repo root):
    python data/synthetic/generate.py
    python data/synthetic/generate.py --out DIR
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = ROOT / "rules"
MARK = "SYNTHETIC — NOT REAL DATA"

NA = None  # truth value: the field does not apply to this order
PENDING = "__PENDING__"  # truth value: awaited, not yet known (e.g. no commitment yet)
NA_TEXT = "Not applicable"
PENDING_TEXT = "To be confirmed"

PRODUCT_RULES = {"EPL": "fields.epl.json", "WAVELENGTH": "fields.wavelength.json"}
G1_RULE = json.loads((RULES_DIR / "gates.json").read_text())["gates"]["G1"]


# --------------------------------------------------------------------------- rules

def load_rules(product: str) -> dict[str, dict]:
    """Return {field_key: rule} for a product, with endpoint fields expanded per end."""
    rules: dict[str, dict] = {}
    for name in ("fields.common.json", PRODUCT_RULES[product]):
        for rule in json.loads((RULES_DIR / name).read_text())["fields"]:
            if rule["scope"] == "endpoint":
                for end in ("a_end", "z_end"):
                    expanded = dict(rule, key=f"{end}.{rule['key']}", end=end)
                    rules[expanded["key"]] = expanded
            else:
                rules[rule["key"]] = rule
    return rules


# ------------------------------------------------------------------- normalization

DATE_FORMATS = ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y")


def parse_date(raw: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognized date: {raw!r}")


def long_date(iso: str) -> str:
    d = parse_date(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def normalize(value_type: str, raw: str):
    raw = raw.strip()
    if value_type == "speed":
        m = re.match(r"(\d+(?:\.\d+)?)\s*([GM])", raw, re.I)
        if not m:
            raise ValueError(f"unrecognized speed: {raw!r}")
        mbps = float(m.group(1)) * (1000 if m.group(2).upper() == "G" else 1)
        return {"value": int(mbps), "unit": "Mbps"}
    if value_type == "date":
        return parse_date(raw).isoformat()
    if value_type == "boolean":
        return raw.lower() in ("yes", "true", "required")
    if value_type == "integer":
        return int(re.sub(r"[^\d]", "", raw))
    if value_type == "list":
        return [item.strip() for item in raw.split(",") if item.strip()]
    if value_type == "enum":
        return raw.lower()
    return raw


# ---------------------------------------------------------------------- templates

END_LABEL = {"a_end": "A end", "z_end": "Z end"}
ENDS = ("a_end", "z_end")

CAPACITY_ROWS = {
    "EPL": [("Port speed", "port_speed"), ("CIR (Committed Information Rate)", "cir")],
    "WAVELENGTH": [("Rate", "rate"), ("Client protocol", "client_protocol")],
}

SERVICE_ROWS = {
    "EPL": [],
    "WAVELENGTH": [
        ("Protection", "protection.type"),
        ("Protection switching time", "protection.switching_time"),
        ("Route diversity required", "route_diversity.required"),
        ("Diverse from circuit IDs", "route_diversity.reference_circuit_ids"),
        ("Diversity evidence required", "route_diversity.required_evidence"),
        ("Maximum latency", "latency.max"),
        ("Latency definition", "latency.definition"),
        ("Latency measurement method", "latency.measurement_method"),
    ],
}

ACCEPTANCE_ROWS = {
    "EPL": [("Required acceptance tests", "acceptance.required_tests")],
    "WAVELENGTH": [
        ("BER test", "acceptance.ber_test"),
        ("BER test duration", "acceptance.ber_test_duration"),
    ],
}

# Service-level parameters (one value per order).
PARAMETER_ROWS = {
    "EPL": [("MTU", "mtu"), ("VLAN", "vlan"), ("L2CP transparency", "l2cp_transparency")],
    "WAVELENGTH": [("FEC (Forward Error Correction)", "fec")],
}

# Handoff interface, one value per end (D25): A and Z can differ.
END_INTERFACE_ROWS = {
    "EPL": [
        ("Handoff interface", "interface.type"),
        ("Optic", "interface.optic"),
        ("Connector", "interface.connector"),
        ("Fiber type", "interface.fiber_type"),
        ("Optic wavelength (nm)", "interface.optic_wavelength_nm"),
    ],
    "WAVELENGTH": [
        ("Client interface", "interface.client_interface"),
        ("Optic", "interface.optic"),
        ("Optic reach", "interface.optic_reach"),
        ("Connector", "interface.connector"),
    ],
}


def end_rows(end: str, product: str) -> list[tuple[str, str]]:
    return [
        ("Address", f"{end}.address"),
        ("Building", f"{end}.building"),
        ("Floor", f"{end}.floor"),
        ("Suite / room", f"{end}.suite_or_room"),
        ("Rack", f"{end}.rack"),
        ("Demarcation point", f"{end}.demarcation_point"),
        *[(label, f"{end}.{key}") for label, key in END_INTERFACE_ROWS[product]],
        ("Data center operator", f"{end}.data_center_operator"),
        ("Meet-Me Room (MMR)", f"{end}.meet_me_room"),
        ("Cross-connect required", f"{end}.cross_connect.required"),
        ("Site access hours", f"{end}.site_access.hours"),
        ("Access notice lead time", f"{end}.site_access.notice_lead_time"),
        ("Escort required", f"{end}.site_access.escort_required"),
        ("Technical contact", f"{end}.technical_contact"),
    ]


def document_templates(product: str, truth: dict) -> list[dict]:
    """Structured documents. Each row is (label, field_key)."""
    xc_ends = [e for e in ENDS if str(truth.get(f"{e}.cross_connect.required", "")).lower() == "yes"]
    docs = [
        {
            "doc_id": "quote",
            "doc_type": "quote",
            "stem": "01_quote",
            "title": "Service Quote",
            "date_style": "long",
            "sections": [
                ("Quote details", [("Customer", "customer_name"), ("Product", "product"),
                                   *CAPACITY_ROWS[product], ("Requested service date", "dates.requested")]),
            ],
        },
        {
            "doc_id": "order_form",
            "doc_type": "order_form",
            "stem": "02_order_form_signed",
            "title": "Service Order Form (signed)",
            "sections": [
                ("Order identification", [("Order ID", "order_id"), ("Customer", "customer_name"),
                                          ("Product", "product"), ("Order version", "order_version"),
                                          ("Carrier circuit ID", "carrier_circuit_id")]),
                ("Service", [*CAPACITY_ROWS[product], *SERVICE_ROWS[product]]),
                ("Handoff interface", [
                    (f"{END_LABEL[e]} {label[0].lower()}{label[1:]}", f"{e}.{key}")
                    for e in ENDS for label, key in END_INTERFACE_ROWS[product][:2]]),
                ("Cross-connect responsibility", [
                    (f"{END_LABEL[e]} cross-connect ordered by", f"{e}.cross_connect.responsibility")
                    for e in ENDS]),
                ("Acceptance", [*ACCEPTANCE_ROWS[product],
                                ("Deemed-acceptance clause", "acceptance.deemed_acceptance_clause"),
                                ("Deemed-acceptance period", "acceptance.deemed_acceptance_period")]),
                ("Dates", [("Requested date", "dates.requested"), ("Forecast date", "dates.forecast"),
                           ("Committed date (FOC)", "dates.committed")]),
                ("Contacts", [("Escalation contact", "escalation_contact")]),
                ("Authorized signature", [("Contract / order form reference", "signature.contract_reference"),
                                          ("Signatory name", "signature.signatory_name"),
                                          ("Signatory title", "signature.signatory_title"),
                                          ("Signature date", "signature.date")]),
            ],
        },
        {
            "doc_id": "technical_annex",
            "doc_type": "technical_annex",
            "stem": "03_technical_annex",
            "title": "Technical Annex — A/Z Sites",
            "sections": [
                ("Service parameters", [("Order ID", "order_id"), *CAPACITY_ROWS[product],
                                        *PARAMETER_ROWS[product]]),
                ("A end", end_rows("a_end", product)),
                ("Z end", end_rows("z_end", product)),
            ],
        },
    ]
    if xc_ends:
        docs.append({
            "doc_id": "loa_cfa",
            "doc_type": "loa_cfa",
            "stem": "04_loa_cfa",
            "title": "Letter of Authorization – Connecting Facility Assignment (LOA-CFA)",
            "sections": [
                (END_LABEL[e], [("LOA-CFA reference", f"{e}.cross_connect.loa_cfa_reference"),
                                ("Data center operator", f"{e}.data_center_operator"),
                                ("Meet-Me Room (MMR)", f"{e}.meet_me_room"),
                                ("Suite / room", f"{e}.suite_or_room"),
                                ("Demarcation point", f"{e}.demarcation_point")])
                for e in xc_ends
            ],
        })
    return docs


# ---------------------------------------------------------------------- rendering

def banner() -> str:
    return f"> **{MARK}**"


VERSION_KEYS = ("cases", "extra_docs", "injections", "labels", "adversarial", "later_gates", "stage", "received_at")


def versions_of(spec: dict) -> list[dict]:
    """A spec is either flat (one version) or carries a "versions" list."""
    if "versions" in spec:
        return spec["versions"]
    return [{k: spec[k] for k in ("truth", "defects", "emails", *VERSION_KEYS) if k in spec}]


def render_documents(spec: dict, version: dict, rules: dict[str, dict], previous: dict | None = None) -> list[dict]:
    """Lay out one version of the package as a list of documents.

    Each document is {"doc_id", "doc_type", "stem", "title", "blocks", "appearances", ...}.
    A block is one of: title, line, para, meta, section, table, note, hidden.
    An appearance says where a field value is shown: {"field_key", "location", "raw_value", "block"}.

    A document listed in version["stale_docs"] was not reissued: it is laid out
    from the previous version, without the current version's defects.
    """
    truth = version["truth"]
    defects = version.get("defects", [])
    stale = set(version.get("stale_docs", []))
    omitted = {d["field"] for d in defects if d["type"] == "omit"}
    overrides = {(d["doc"], d["field"]): d["value"] for d in defects if d["type"] == "mismatch"}
    labels = version.get("labels", {})
    injections = {i["doc"]: i for i in version.get("injections", [])}
    documents: list[dict] = []

    for template in document_templates(spec["product"], truth):
        doc_id = template["doc_id"]
        is_stale = doc_id in stale
        doc_truth = previous["truth"] if is_stale else truth
        blocks = [{"t": "title", "text": template["title"]},
                  {"t": "line", "text": f"{spec['tenant']} · Order {truth['order_id']} · "
                                        f"Version {doc_truth['order_version']}"}]
        appearances = [{"field_key": "order_version", "location": "header › Version",
                        "raw_value": doc_truth["order_version"], "block": 1}]
        for n, (heading, rows) in enumerate(template["sections"], start=1):
            shown_rows = []
            for label, key in rows:
                label = labels.get(key, label) if doc_id == "order_form" else label
                value = doc_truth[key] if is_stale else overrides.get((doc_id, key), truth[key])
                if key in omitted and not is_stale:
                    text = ""
                elif value is NA:
                    text = NA_TEXT
                elif value == PENDING:
                    text = PENDING_TEXT
                elif rules[key]["value_type"] == "date" and template.get("date_style") == "long":
                    text = long_date(value)
                else:
                    text = value
                shown_rows.append((label, text))
                if text and text != PENDING_TEXT:
                    appearances.append({"field_key": key, "location": f"§{n} {heading} › {label}",
                                        "raw_value": text, "block": len(blocks)})
            blocks.append({"t": "section", "n": n, "heading": heading, "rows": shown_rows})
        if doc_id == "quote":
            blocks.append({"t": "para", "text":
                           "Pricing (synthetic): monthly recurring charge USD 4,200; non-recurring charge USD 1,500. "
                           "Quote valid for 30 days. Dates in this quote are customer requests, not commitments."})
        if doc_id == "order_form":
            signed_by = "" if "signature.signatory_name" in omitted else doc_truth["signature.signatory_name"]
            blocks.append({"t": "para", "text": f"Signed: /s/ {signed_by} (synthetic signature)" if signed_by
                           else "Signed: (signature block left blank)"})
        if doc_id in injections:
            injection = injections[doc_id]
            blocks.append({"t": "hidden" if injection.get("style") == "hidden" else "note",
                           "text": injection["text"]})
        documents.append({"doc_id": doc_id, "doc_type": template["doc_type"], "stem": template["stem"],
                          "title": template["title"], "blocks": blocks, "appearances": appearances,
                          "stale": is_stale, "foreign": False, "single_page": False})

    emails = version.get("emails", [])
    for i, mail in enumerate(emails, start=1):
        mail["doc_id"] = f"email_{i:02d}"
        blocks = [{"t": "title", "text": f"Email: {mail['subject']}"},
                  {"t": "meta", "items": [("From", mail["from"]), ("To", mail["to"]), ("Sent", mail["sent"]),
                                          ("Subject", mail["subject"])]}]
        blocks += [{"t": "para", "text": paragraph} for paragraph in mail["body"]]
        documents.append({"doc_id": mail["doc_id"], "doc_type": "email", "stem": f"{4 + i:02d}_email_{i:02d}",
                          "title": mail["subject"], "blocks": blocks,
                          "appearances": [dict(a, block=0) for a in mail.get("appearances", [])],
                          "stale": False, "foreign": bool(mail.get("foreign")), "single_page": True})

    for j, extra in enumerate(version.get("extra_docs", []), start=1):
        blocks = [{"t": "title", "text": extra["title"]}, {"t": "line", "text": extra["header"]}]
        blocks += [{"t": "para", "text": paragraph} for paragraph in extra.get("paragraphs", [])]
        if extra.get("table"):
            blocks.append({"t": "table", **extra["table"]})
        documents.append({"doc_id": extra["doc_id"], "doc_type": extra["doc_type"],
                          "stem": f"{4 + len(emails) + j:02d}_{extra['slug']}", "title": extra["title"],
                          "blocks": blocks, "appearances": [dict(a, block=0) for a in extra.get("appearances", [])],
                          "stale": False, "foreign": bool(extra.get("foreign")), "single_page": True})
    return documents


def to_markdown(blocks: list[dict]) -> str:
    """Review copy of a document. The PDF is the document of record (D30)."""
    lines = [banner(), ""]
    for block in blocks:
        kind = block["t"]
        if kind == "title":
            lines += [f"# {block['text']}", ""]
        elif kind in ("line", "para"):
            lines += [block["text"], ""]
        elif kind == "meta":
            lines += [f"- **{key}:** {value}" for key, value in block["items"]] + [""]
        elif kind == "section":
            lines += [f"## {block['n']}. {block['heading']}", "", "| Field | Value |", "|---|---|"]
            lines += [f"| {label} | {value} |" for label, value in block["rows"]] + [""]
        elif kind == "table":
            lines += ["| " + " | ".join(block["columns"]) + " |", "|" + "---|" * len(block["columns"])]
            lines += ["| " + " | ".join(row) + " |" for row in block["rows"]] + [""]
        elif kind == "note":
            lines += [f"*{block['text']}*", ""]
        elif kind == "hidden":
            lines += [f"<!-- hidden text in the PDF: {block['text']} -->", ""]
    lines.append(banner())
    return "\n".join(lines) + "\n"


def write_documents(version_dir: Path, documents: list[dict]) -> tuple[dict, list[dict]]:
    """Write each document as PDF (documents/) and Markdown (markdown/).

    Returns (appearances by field, document list for the golden label).
    """
    from pdf import build_pdf

    (version_dir / "documents").mkdir(parents=True, exist_ok=True)
    (version_dir / "markdown").mkdir(parents=True, exist_ok=True)
    appearances: dict[str, list[dict]] = {}
    listing = []
    for doc in documents:
        filename = f"{doc['stem']}.pdf"
        pages, block_pages = build_pdf(version_dir / "documents" / filename, doc["title"], doc["blocks"])
        if doc["single_page"] and pages != 1:
            raise ValueError(f"{version_dir}: {filename} must fit on one page, got {pages}")
        (version_dir / "markdown" / f"{doc['stem']}.md").write_text(to_markdown(doc["blocks"]), encoding="utf-8")
        for a in doc["appearances"]:
            appearances.setdefault(a["field_key"], []).append({
                "doc_id": doc["doc_id"], "page": block_pages[a["block"]],
                "location": a["location"], "raw_value": a["raw_value"]})
        listing.append({"doc_id": doc["doc_id"], "doc_type": doc["doc_type"], "filename": filename,
                        "pages": pages, "stale": doc["stale"], "foreign": doc["foreign"]})
    return appearances, listing


# -------------------------------------------------------------------------- golden

def check_conditions(version: dict, rules: dict[str, dict]) -> None:
    """The truth must respect applies_when, so a spec cannot contradict the rules."""
    truth = version["truth"]
    for key, rule in rules.items():
        if key not in truth:
            raise ValueError(f"{truth['order_id']}: truth is missing field {key}")
        cond = rule.get("applies_when")
        if not cond:
            continue
        driver = cond["field"]
        if rule["scope"] == "endpoint":
            driver = f"{rule['end']}.{driver}"
        driver_value = truth[driver]
        if "equals" in cond:
            applies = isinstance(driver_value, str) and driver_value.lower() == cond["equals"].lower()
        else:
            applies = driver_value is not NA and driver_value != PENDING
        if applies and truth[key] is NA:
            raise ValueError(f"{truth['order_id']}: {key} must have a value because {driver} = {driver_value!r}")
        if not applies and truth[key] is not NA:
            raise ValueError(f"{truth['order_id']}: {key} must be not applicable because {driver} = {driver_value!r}")


def shown(value):
    return NA_TEXT if value is NA else PENDING_TEXT if value == PENDING else value


def version_change(previous: dict, previous_golden: dict, version: dict, rules: dict[str, dict]) -> dict:
    """What changed between two versions, computed from the two truths."""
    changed = [{"field_key": key, "previous": shown(previous["truth"][key]), "current": shown(version["truth"][key])}
               for key in rules
               if key != "order_version" and previous["truth"][key] != version["truth"][key]]
    impact = version.get("milestone_impact", {"expected": False, "note": "No date or scope change."})
    return {
        "previous_version_no": previous_golden["order"]["version_no"],
        "previous_gate_recommendation": previous_golden["expected_gate"]["recommendation"],
        "changed_fields": changed,
        "reopened_validations": [c["field_key"] for c in changed],
        "milestone_impact_expected": impact["expected"],
        "milestone_impact_note": impact["note"],
    }


def build_golden(spec: dict, version: dict, rules: dict[str, dict], appearances: dict, documents: list[dict],
                 previous: dict | None = None, previous_golden: dict | None = None) -> dict:
    truth = version["truth"]
    order_id = truth["order_id"]
    expected_fields = []
    for key, rule in rules.items():
        sources = appearances.get(key, [])
        real = [s for s in sources if s["raw_value"] != NA_TEXT]
        if not sources:
            # A field that does not apply may have no row at all (e.g. no LOA-CFA section for an
            # end without a cross-connect).
            status = "pending" if truth[key] == PENDING else "not_applicable" if truth[key] is NA else "missing"
            raw, norm = None, None
        elif not real:
            status, raw, norm = "not_applicable", None, None
        else:
            normalized = [normalize(rule["value_type"], s["raw_value"]) for s in real]
            if any(n != normalized[0] for n in normalized):
                status, raw, norm = "contradictory", None, None
            else:
                authoritative = next((s for s in real if s["doc_id"] == rule["authoritative_source"]), real[0])
                status, raw, norm = "pending", authoritative["raw_value"], normalized[0]
        expected_fields.append({"field_key": key, "expected_status": status, "raw_value": raw,
                                "normalized_value": norm, "sources": sources})

    by_key = {f["field_key"]: f for f in expected_fields}
    findings = []
    for n, defect in enumerate((d for d in version.get("defects", []) if "finding" in d), start=1):
        f = defect["finding"]
        field = by_key[defect["field"]]
        findings.append({
            "finding_id": f"F{n}",
            "rule_id": f["rule_id"],
            "field_key": defect["field"],
            "severity": f.get("severity") or rules[defect["field"]]["missing_severity"],
            "mandatory_case": f.get("mandatory_case"),
            "conflicting_values": field["sources"] if field["expected_status"] == "contradictory" else [],
            "description": f["description"],
        })

    # Labels are known by construction only if defects and findings line up exactly. A segregation
    # finding (SEG-*, Phase 7) can stand without a defective field: an email naming another
    # customer is a finding, not a field contradiction (D35).
    defective = {f["field_key"] for f in expected_fields if f["expected_status"] in G1_RULE["blocking_statuses"]}
    reported = {f["field_key"] for f in findings}
    segregation_only = {f["field_key"] for f in findings if f["rule_id"].startswith("SEG-")} - defective
    if defective != reported - segregation_only:
        raise ValueError(f"{order_id} v{truth['order_version']}: defective fields {sorted(defective)} "
                         f"do not match findings {sorted(reported)}")

    # G1 (D28): pending is enough; only missing or contradictory fields raise findings, and a
    # finding blocks when its severity is a blocking severity. "verified" is never required.
    blocking = [f["finding_id"] for f in findings if f["severity"] in G1_RULE["blocking_severities"]]

    dates = [{"doc_id": s["doc_id"], "page": s["page"], "location": s["location"], "raw_value": s["raw_value"],
              "date": parse_date(s["raw_value"]).isoformat(), "type": "requested", "scope": "order",
              "is_commitment": False, "mandatory_case": None, "note": "Customer requested date."}
             for s in appearances.get("dates.requested", [])]
    dates += [{"doc_id": s["doc_id"], "page": s["page"], "location": s["location"], "raw_value": s["raw_value"],
               "date": parse_date(s["raw_value"]).isoformat(), "type": "committed", "scope": "order",
               "is_commitment": True, "mandatory_case": None,
               "note": "Carrier committed date stated in the signed order form (FOC = committed, D19)."}
              for s in appearances.get("dates.committed", []) if s["raw_value"] != NA_TEXT]
    dependencies = []
    for mail in version.get("emails", []):
        for m in mail.get("date_mentions", []):
            dates.append({"doc_id": mail["doc_id"], "page": 1, "location": m["location"], "raw_value": m["raw_value"],
                          "date": parse_date(m["raw_value"]).isoformat(), "type": m["type"],
                          "scope": m.get("scope", "order"),
                          "is_commitment": m["type"] == "committed" and m.get("scope", "order") == "order",
                          "mandatory_case": m.get("mandatory_case"), "note": m["note"]})
        if "dependency" in mail:
            dependencies.append({"dependency_id": f"D{len(dependencies) + 1}", "source_doc_id": mail["doc_id"],
                                 **mail["dependency"]})

    cases = set(version.get("cases", []))
    cases |= {f["mandatory_case"] for f in findings if f["mandatory_case"]}
    cases |= {d["mandatory_case"] for d in dates if d["mandatory_case"]}
    cases |= {d["mandatory_case"] for d in dependencies if d.get("mandatory_case")}
    cases |= {g["mandatory_case"] for g in version.get("later_gates", []) if g.get("mandatory_case")}

    return {
        "synthetic": True,
        "synthetic_mark": MARK,
        "order": {
            "external_order_id": order_id,
            "product": spec["product"],
            "version_no": int(truth["order_version"]),
            "received_at": version["received_at"],
            "stage": version.get("stage", "order_received"),
            "tenant": spec["tenant"],
            "customer": spec["customer"],
            "customer_type": spec["customer_type"],
            "project": spec.get("project"),
            "split": spec["split"],
            "category": spec["category"],
        },
        "mandatory_cases": sorted(cases),
        "documents": documents,
        "expected_fields": expected_fields,
        "expected_findings": findings,
        "expected_gate": {"gate": "G1", "recommendation": "block" if blocking else "pass",
                          "blocking_finding_ids": blocking},
        "expected_later_gates": version.get("later_gates", []),
        "expected_dates": dates,
        "expected_dependencies": dependencies,
        "expected_version_change": (version_change(previous, previous_golden, version, rules)
                                    if previous else None),
        "shared_resources": spec.get("shared_resources", []),
        "adversarial": version.get("adversarial"),
        "seeded_defects": [{"defect_type": d["type"], "field": d.get("field"), "description": d["description"]}
                           for d in version.get("defects", [])],
    }


# ---------------------------------------------------------------------------- main

def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def generate_order(spec: dict, orders_dir: Path) -> dict:
    """Write every version of one order. Returns its manifest entry."""
    spec = json.loads(json.dumps(spec))  # deep copy; None and strings survive
    rules = load_rules(spec["product"])
    order_id = None
    previous = previous_golden = None
    cases: set[int] = set()
    version_nos = []
    for version in versions_of(spec):
        check_conditions(version, rules)
        order_id = version["truth"]["order_id"]
        version_dir = orders_dir / order_id / f"v{int(version['truth']['order_version'])}"
        appearances, documents = write_documents(version_dir, render_documents(spec, version, rules, previous))
        golden = build_golden(spec, version, rules, appearances, documents, previous, previous_golden)
        dump(version_dir / "golden.json", golden)
        cases |= set(golden["mandatory_cases"])
        version_nos.append(golden["order"]["version_no"])
        previous, previous_golden = version, golden
    return {"order_id": order_id, "product": spec["product"], "category": spec["category"],
            "split": spec["split"], "customer": spec["customer"], "customer_type": spec["customer_type"],
            "project": spec.get("project"), "versions": version_nos, "mandatory_cases": sorted(cases),
            "path": f"orders/{order_id}"}


def generate(out_dir: Path, specs: list[dict] | None = None, event_sets: list[dict] | None = None) -> dict:
    """Write the whole dataset under out_dir and return the manifest."""
    import dataset
    import event_sets as event_module

    specs = dataset.ALL_ORDERS if specs is None else specs
    event_sets = event_module.EVENT_SETS if event_sets is None else event_sets
    for generated in ("orders", "events"):
        shutil.rmtree(out_dir / generated, ignore_errors=True)

    orders = sorted((generate_order(spec, out_dir / "orders") for spec in specs), key=lambda o: o["order_id"])
    events = []
    for event_set in event_sets:
        filename = f"{event_set['event_set_id']}.json"
        dump(out_dir / "events" / filename, {"synthetic": True, "synthetic_mark": MARK, **event_set})
        events.append({"event_set_id": event_set["event_set_id"], "mandatory_case": event_set["mandatory_case"],
                       "path": f"events/{filename}"})

    cases = {}
    for number, (title, where, phase) in dataset.MANDATORY_CASES.items():
        cases[str(number)] = {
            "title": title, "tested_in": where, "phase": phase,
            "orders": [o["order_id"] for o in orders if number in o["mandatory_cases"]],
            "events": [e["event_set_id"] for e in events if e["mandatory_case"] == number],
        }
    manifest = {
        "synthetic": True,
        "synthetic_mark": MARK,
        "tenant": dataset.TENANT,
        "segregation_tenant": dataset.SECOND_TENANT,
        "counts": {
            "orders": len(orders),
            "by_split": {s: sum(o["split"] == s for o in orders) for s in ("dev", "eval", "adversarial")},
            "by_category": {c: sum(o["category"] == c for o in orders) for c in ("clean", "defect", "adversarial")},
            "by_product": {p: sum(o["product"] == p for o in orders) for p in ("EPL", "WAVELENGTH")},
            "order_versions": sum(len(o["versions"]) for o in orders),
            "event_sets": len(events),
        },
        "orders": orders,
        "events": events,
        "mandatory_cases": cases,
    }
    dump(out_dir / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = generate(args.out)
    print(json.dumps(result["counts"], indent=2))
