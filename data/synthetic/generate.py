"""Synthetic order generator.

SYNTHETIC — NOT REAL DATA. Every company, person, address and identifier
produced here is fictional.

Each order starts from a "truth" (the correct value of every critical field).
Defects are seeded on purpose, so the golden label is known by construction:
the generator writes the documents and the expected answers from the same spec.

Phase 1 status: produces the two example orders for review (D24). The rest of
the dataset is generated after Dante reviews them.

Usage:
    python data/synthetic/generate.py              # writes data/synthetic/examples/
    python data/synthetic/generate.py --out DIR
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path

from example_orders import EXAMPLE_ORDERS

ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = ROOT / "rules"
MARK = "SYNTHETIC — NOT REAL DATA"

NA = None  # truth value: the field does not apply to this order
PENDING = "__PENDING__"  # truth value: awaited, not yet known (e.g. no commitment yet)
NA_TEXT = "Not applicable"
PENDING_TEXT = "To be confirmed"

PRODUCT_RULES = {"EPL": "fields.epl.json", "WAVELENGTH": "fields.wavelength.json"}


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

INTERFACE_ROWS = {
    "EPL": [
        ("Handoff interface", "interface.type"),
        ("Optic", "interface.optic"),
        ("Connector", "interface.connector"),
        ("Fiber type", "interface.fiber_type"),
        ("Optic wavelength (nm)", "interface.optic_wavelength_nm"),
        ("MTU", "mtu"),
        ("VLAN", "vlan"),
        ("L2CP transparency", "l2cp_transparency"),
    ],
    "WAVELENGTH": [
        ("Client interface", "interface.client_interface"),
        ("Optic", "interface.optic"),
        ("Optic reach", "interface.optic_reach"),
        ("Connector", "interface.connector"),
        ("FEC (Forward Error Correction)", "fec"),
    ],
}


def end_rows(end: str) -> list[tuple[str, str]]:
    return [
        ("Address", f"{end}.address"),
        ("Building", f"{end}.building"),
        ("Floor", f"{end}.floor"),
        ("Suite / room", f"{end}.suite_or_room"),
        ("Rack", f"{end}.rack"),
        ("Demarcation point", f"{end}.demarcation_point"),
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
    xc_ends = [e for e in ("a_end", "z_end") if str(truth.get(f"{e}.cross_connect.required", "")).lower() == "yes"]
    docs = [
        {
            "doc_id": "quote",
            "doc_type": "quote",
            "filename": "01_quote.md",
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
            "filename": "02_order_form_signed.md",
            "title": "Service Order Form (signed)",
            "sections": [
                ("Order identification", [("Order ID", "order_id"), ("Customer", "customer_name"),
                                          ("Product", "product"), ("Order version", "order_version"),
                                          ("Carrier circuit ID", "carrier_circuit_id")]),
                ("Service", [*CAPACITY_ROWS[product], *SERVICE_ROWS[product]]),
                ("Cross-connect responsibility", [
                    (f"{END_LABEL[e]} cross-connect ordered by", f"{e}.cross_connect.responsibility")
                    for e in ("a_end", "z_end")]),
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
            "filename": "03_technical_annex.md",
            "title": "Technical Annex — A/Z Sites",
            "sections": [
                ("Service and interface", [("Order ID", "order_id"), *CAPACITY_ROWS[product][:2],
                                           *INTERFACE_ROWS[product]]),
                ("A end", end_rows("a_end")),
                ("Z end", end_rows("z_end")),
            ],
        },
    ]
    if xc_ends:
        docs.append({
            "doc_id": "loa_cfa",
            "doc_type": "loa_cfa",
            "filename": "04_loa_cfa.md",
            "title": "Letter of Authorization – Connecting Facility Assignment (LOA-CFA)",
            "sections": [
                (END_LABEL[e], [("LOA-CFA reference", f"{e}.cross_connect.loa_cfa_reference"),
                                ("Data center operator", f"{e}.data_center_operator"),
                                ("Meet-Me Room (MMR)", f"{e}.meet_me_room"),
                                ("Demarcation point", f"{e}.demarcation_point")])
                for e in xc_ends
            ],
        })
    return docs


# ---------------------------------------------------------------------- rendering

def banner() -> str:
    return f"> **{MARK}**"


def render_documents(spec: dict, rules: dict[str, dict]):
    """Render the structured documents. Returns (files, appearances).

    appearances: {field_key: [{"doc_id", "location", "raw_value"}]}
    """
    truth = spec["truth"]
    omitted = {d["field"] for d in spec["defects"] if d["type"] == "omit"}
    overrides = {(d["doc"], d["field"]): d["value"] for d in spec["defects"] if d["type"] == "mismatch"}

    files: dict[str, str] = {}
    appearances: dict[str, list[dict]] = {}

    for doc in document_templates(spec["product"], truth):
        lines = [banner(), "", f"# {doc['title']}", "",
                 f"{spec['tenant']} · Order {truth['order_id']} · Version {truth['order_version']}", ""]
        for n, (heading, rows) in enumerate(doc["sections"], start=1):
            lines += [f"## {n}. {heading}", "", "| Field | Value |", "|---|---|"]
            for label, key in rows:
                value = overrides.get((doc["doc_id"], key), truth[key])
                if key in omitted:
                    shown = ""
                elif value is NA:
                    shown = NA_TEXT
                elif value == PENDING:
                    shown = PENDING_TEXT
                elif rules[key]["value_type"] == "date" and doc.get("date_style") == "long":
                    shown = long_date(value)
                else:
                    shown = value
                lines.append(f"| {label} | {shown} |")
                if shown and shown != PENDING_TEXT:
                    appearances.setdefault(key, []).append({
                        "doc_id": doc["doc_id"],
                        "location": f"§{n} {heading} › {label}",
                        "raw_value": shown,
                    })
            lines.append("")
        if doc["doc_id"] == "quote":
            lines += ["Pricing (synthetic): monthly recurring charge USD 4,200; non-recurring charge USD 1,500. "
                      "Quote valid for 30 days. Dates in this quote are customer requests, not commitments.", ""]
        if doc["doc_id"] == "order_form":
            lines += [f"Signed: /s/ {truth['signature.signatory_name']} (synthetic signature)", ""]
        lines.append(banner())
        files[doc["filename"]] = "\n".join(lines) + "\n"

    for i, mail in enumerate(spec["emails"], start=1):
        filename = f"{4 + i:02d}_email_{i:02d}.md"
        mail["doc_id"] = f"email_{i:02d}"
        mail["filename"] = filename
        body = "\n\n".join(mail["body"])
        files[filename] = "\n".join([
            banner(), "", f"# Email: {mail['subject']}", "",
            f"- **From:** {mail['from']}", f"- **To:** {mail['to']}",
            f"- **Sent:** {mail['sent']}", f"- **Subject:** {mail['subject']}", "",
            body, "", banner(),
        ]) + "\n"
    return files, appearances


# -------------------------------------------------------------------------- golden

def check_conditions(spec: dict, rules: dict[str, dict]) -> None:
    """The truth must respect applies_when, so a spec cannot contradict the rules."""
    truth = spec["truth"]
    for key, rule in rules.items():
        if key not in truth:
            raise ValueError(f"{spec['truth']['order_id']}: truth is missing field {key}")
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
            raise ValueError(f"{key} must have a value because {driver} = {driver_value!r}")
        if not applies and truth[key] is not NA:
            raise ValueError(f"{key} must be not applicable because {driver} = {driver_value!r}")


def build_golden(spec: dict, rules: dict[str, dict], files: dict[str, str], appearances: dict) -> dict:
    truth = spec["truth"]
    expected_fields = []
    for key, rule in rules.items():
        sources = appearances.get(key, [])
        real = [s for s in sources if s["raw_value"] != NA_TEXT]
        if not sources:
            status = "pending" if truth[key] == PENDING else "missing"
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
    for n, defect in enumerate((d for d in spec["defects"] if "finding" in d), start=1):
        f = defect["finding"]
        findings.append({
            "finding_id": f"F{n}",
            "rule_id": f["rule_id"],
            "field_key": defect["field"],
            "severity": f["severity"],
            "mandatory_case": f.get("mandatory_case"),
            "conflicting_values": by_key[defect["field"]]["sources"] if defect["type"] == "mismatch" else [],
            "description": f["description"],
        })
    blocking = [f["finding_id"] for f in findings if f["severity"] == "critical"]

    dates = [{"doc_id": s["doc_id"], "location": s["location"], "raw_value": s["raw_value"],
              "date": parse_date(s["raw_value"]).isoformat(), "type": "requested", "is_commitment": False,
              "mandatory_case": None, "note": "Customer requested date."}
             for s in appearances.get("dates.requested", [])]
    for mail in spec["emails"]:
        for m in mail.get("date_mentions", []):
            dates.append({"doc_id": mail["doc_id"], "location": m["location"], "raw_value": m["raw_value"],
                          "date": parse_date(m["raw_value"]).isoformat(), "type": m["type"],
                          "is_commitment": m["type"] == "committed",
                          "mandatory_case": m.get("mandatory_case"), "note": m["note"]})

    templates = document_templates(spec["product"], truth)
    documents = [{"doc_id": d["doc_id"], "doc_type": d["doc_type"], "filename": d["filename"]} for d in templates]
    documents += [{"doc_id": m["doc_id"], "doc_type": "email", "filename": m["filename"]} for m in spec["emails"]]

    return {
        "synthetic": True,
        "synthetic_mark": MARK,
        "order": {
            "external_order_id": truth["order_id"],
            "product": spec["product"],
            "version_no": 1,
            "tenant": spec["tenant"],
            "customer": truth["customer_name"],
            "customer_type": spec["customer_type"],
            "project": spec.get("project"),
            "split": spec["split"],
        },
        "documents": documents,
        "expected_fields": expected_fields,
        "expected_findings": findings,
        "expected_gate": {"gate": "G1", "recommendation": "block" if blocking else "pass",
                          "blocking_finding_ids": blocking},
        "expected_dates": dates,
        "shared_resources": spec.get("shared_resources", []),
        "seeded_defects": [{"defect_type": d["type"], "field": d.get("field"), "description": d["description"]}
                           for d in spec["defects"]],
    }


# ---------------------------------------------------------------------------- main

def generate(out_dir: Path, specs: list[dict] = EXAMPLE_ORDERS) -> list[Path]:
    written = []
    for spec in specs:
        spec = json.loads(json.dumps(spec))  # deep copy; None and strings survive
        rules = load_rules(spec["product"])
        check_conditions(spec, rules)
        files, appearances = render_documents(spec, rules)
        golden = build_golden(spec, rules, files, appearances)
        order_dir = out_dir / spec["truth"]["order_id"]
        (order_dir / "documents").mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (order_dir / "documents" / name).write_text(text, encoding="utf-8")
        (order_dir / "golden.json").write_text(
            json.dumps(golden, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(order_dir)
    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "examples")
    args = parser.parse_args()
    for path in generate(args.out):
        print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
