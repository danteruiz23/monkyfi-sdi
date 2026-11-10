# rules

Rules as JSON, readable by Python and TypeScript.

- `fields.common.json`, `fields.epl.json`, `fields.wavelength.json` — critical fields per product (SPEC 8.4, validated: D19). Handoff interface fields are per endpoint (D25). `missing_severity` values are accepted as defaults (D29); `authoritative_source` is a Proposed default.
- `severity.json` — severity levels and the tie-break rule (SPEC 8.3, validated: D20).
- `synonyms.json` — label synonyms for extraction, including FOC date = committed date (D19).
- `extraction.json` — Phase 2, Proposed: document type from the title, which document types can set a field value (emails cannot), and the placeholder texts for not applicable and awaited values.
- `gates.json` — the G1 pass condition (D28): consistent critical fields with nothing missing or contradictory; `verified` is never required. Other gates are added in their phases.

- `findings.json` — Phase 3, Proposed: which rule names a finding (first match wins) and its action, the owner role per field group, due dates in business days per severity, and which changed fields may affect the plan when a new order version arrives. Due dates accepted as proposals (D44). Owners decided (D46): an internal owner and a resolving party per field group, with per-field exceptions. `customer_scoping` configures the segregation finding (D42).

- `stages.json` — the 11 delivery stages (SPEC 6) with equal weights, the gate that closes each stage and the Presales assumption (D45, D47). Read by the web view.

The field files are checked against `schemas/field_rules.schema.json` by the tests. Changing a rule requires re-running the evals.

- `dates.json` — Phase 4, Proposed: how every date is typed requested / forecast / committed. Quote and order form keep the type of the field (FOC date = committed, D19). An email date is typed from its sentence by ordered cue rules; an email never gives the order a committed date (D35); a firm supplier date is committed only on the supplier dependency and only from a registered supplier (D26); within one email the tentative reading of a date wins. A committed order date is used only with an approval record.
