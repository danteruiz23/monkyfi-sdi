"""Build the Phase 1 review sample: 6 random orders from the split plus the severity table.

SYNTHETIC — NOT REAL DATA.

Usage (from the repo root):
    python data/synthetic/review_sample.py [--seed N]     # writes docs/PHASE1_SAMPLE.md
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MARK = "SYNTHETIC — NOT REAL DATA"
SAMPLE_SIZE = 6
DEFAULT_SEED = 20261109


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def order_section(entry: dict) -> list[str]:
    lines = [f"## {entry['order_id']} — {entry['product']}, {entry['customer']}", "",
             f"Split: {entry['split']} · Category: {entry['category']} · Versions: "
             f"{', '.join(f'v{v}' for v in entry['versions'])} · Mandatory cases: "
             f"{', '.join(map(str, entry['mandatory_cases'])) or 'none'}", ""]
    for version_no in entry["versions"]:
        version_dir = HERE / entry["path"] / f"v{version_no}"
        golden = load(version_dir / "golden.json")
        gate = golden["expected_gate"]
        lines += [f"### Version {version_no} — expected G1: **{gate['recommendation']}**", "",
                  f"PDFs: `data/synthetic/{entry['path']}/v{version_no}/documents/`", ""]
        if golden["seeded_defects"]:
            lines += ["Seeded on purpose:", ""] + [f"- {d['description']}" for d in golden["seeded_defects"]] + [""]
        else:
            lines += ["Nothing seeded: the agent must report no findings.", ""]
        if golden["expected_findings"]:
            lines += ["| Finding | Field | Severity | Blocks G1 | Values in conflict | Why |", "|---|---|---|---|---|---|"]
            for f in golden["expected_findings"]:
                values = "; ".join(f"{s['doc_id']} p.{s['page']}: {s['raw_value']}" for s in f["conflicting_values"])
                lines.append(f"| {f['finding_id']} | `{f['field_key']}` | {f['severity']} | "
                             f"{'yes' if f['finding_id'] in gate['blocking_finding_ids'] else 'no'} | "
                             f"{cell(values) or '(missing in every document)'} | {cell(f['description'])} |")
            lines.append("")
        change = golden["expected_version_change"]
        if change:
            lines += [f"Changed since version {change['previous_version_no']} (only these validations reopen):", ""]
            lines += [f"- `{c['field_key']}`: {c['previous']} → {c['current']}" for c in change["changed_fields"]]
            lines += ["", f"Milestone impact expected: {'yes' if change['milestone_impact_expected'] else 'no'}. "
                          f"{change['milestone_impact_note']}", ""]
        lines += ["| Date | Type | Scope | Order commitment | Source |", "|---|---|---|---|---|"]
        lines += [f"| {d['date']} | {d['type']} | {d['scope']} | {'yes' if d['is_commitment'] else 'no'} | "
                  f"{d['doc_id']} p.{d['page']}, {cell(d['location'])} |" for d in golden["expected_dates"]]
        lines.append("")
        for dep in golden["expected_dependencies"]:
            lines += [f"Dependency: {dep['description']} ({dep['supplier']}). Supplier date: "
                      f"{dep['supplier_date'] or 'none'} ({dep['supplier_date_type'] or 'no date'}). "
                      f"Order forecast: {dep['order_forecast_status']}. {dep['note']}", ""]
        for later in golden["expected_later_gates"]:
            unmet = "; ".join(later["unmet_requirements"]) or "nothing unmet"
            lines += [f"Expected {later['gate']}: **{later['recommendation']}** — {unmet}", ""]
        for resource in golden["shared_resources"]:
            lines += [f"Shared resource `{resource['shared_resource_id']}` (blocked: {resource['is_blocked']}), "
                      f"linked to {', '.join(resource['linked_order_ids'])}.", ""]
        for doc in golden["documents"]:
            text = (version_dir / "markdown" / f"{doc['filename'][:-4]}.md").read_text(encoding="utf-8")
            # Headings become bold lines so the documents do not clutter this file's outline.
            text = "\n".join(f"**{line.lstrip('# ')}**" if line.startswith("#") else line for line in text.splitlines())
            flag = " — NOT REISSUED (previous version)" if doc["stale"] else ""
            lines += ["<details>", f"<summary>{doc['filename']} ({doc['doc_type']}, {doc['pages']} page(s)){flag}</summary>",
                      "", text.rstrip(), "", "</details>", ""]
    return lines


def severity_section() -> list[str]:
    severity = load(ROOT / "rules" / "severity.json")
    lines = ["## Severity table", "",
             "Levels (SPEC 8.3, D20). Only critical findings block a gate.", "",
             "| Level | Criterion | Blocks gate |", "|---|---|---|"]
    lines += [f"| {level['level']} | {level['criterion']} | {'yes' if level['blocks_gate'] else 'no'} |"
              for level in severity["levels"]]
    lines += ["", f"Always critical: {', '.join(severity['levels'][0]['always_critical'])}. "
                  f"Tie-break: {severity['tie_break']['rule']} The agent never lowers a severity.", "",
              "Severity of the finding raised when a field is missing (accepted as defaults, D29). A contradictory "
              "field takes the same severity (Proposed). Per-end fields apply to both the A end and the Z end.", ""]
    for title, name in (("Both products", "fields.common.json"), ("EPL only", "fields.epl.json"),
                        ("Wavelength only", "fields.wavelength.json")):
        lines += [f"### {title}", "", "| Field | Group | Per | Required | Severity if missing | Authoritative source |",
                  "|---|---|---|---|---|---|"]
        for rule in load(ROOT / "rules" / name)["fields"]:
            required = "always" if rule["requirement"] == "required" else f"when: {rule['condition']}"
            lines.append(f"| `{rule['key']}` | {rule['group']} | {'end' if rule['scope'] == 'endpoint' else 'order'} | "
                         f"{cell(required)} | {rule['missing_severity']} | {rule['authoritative_source']} |")
        lines.append("")
    return lines


def build(seed: int) -> str:
    manifest = load(HERE / "manifest.json")
    split = sorted(o["order_id"] for o in manifest["orders"] if o["split"] in ("dev", "eval"))
    chosen = sorted(random.Random(seed).sample(split, SAMPLE_SIZE))
    entries = {o["order_id"]: o for o in manifest["orders"]}
    lines = [f"> **{MARK}**", "", "# Phase 1 review sample", "",
             f"Six orders drawn at random from the {len(split)} orders in the development and evaluation split "
             f"(`random.Random({seed}).sample`, order IDs sorted first), followed by the severity table. "
             "Generated by `data/synthetic/review_sample.py`; do not edit by hand.", "",
             "Each order shows what was seeded, what the agent is expected to find, and every document of the "
             "package. The documents of record are the PDFs; the text shown here is the Markdown copy of each one.", "",
             "| Order | Product | Customer | Split | Category | Mandatory cases |", "|---|---|---|---|---|---|"]
    lines += [f"| {e['order_id']} | {e['product']} | {e['customer']} | {e['split']} | {e['category']} | "
              f"{', '.join(map(str, e['mandatory_cases'])) or '—'} |" for e in (entries[c] for c in chosen)]
    lines.append("")
    for order_id in chosen:
        lines += order_section(entries[order_id])
    lines += severity_section()
    lines += [f"> **{MARK}**"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    out = ROOT / "docs" / "PHASE1_SAMPLE.md"
    out.write_text(build(args.seed), encoding="utf-8")
    print(out.relative_to(ROOT))
