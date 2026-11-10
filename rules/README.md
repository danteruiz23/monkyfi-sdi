# rules

Rules as JSON, readable by Python and TypeScript.

- `fields.common.json`, `fields.epl.json`, `fields.wavelength.json` — critical fields per product (SPEC 8.4, validated: D19). Handoff interface fields are per endpoint (D25). `missing_severity` values are accepted as defaults (D29); `authoritative_source` is a Proposed default.
- `severity.json` — severity levels and the tie-break rule (SPEC 8.3, validated: D20).
- `synonyms.json` — label synonyms for extraction, including FOC date = committed date (D19).
- `gates.json` — the G1 pass condition (D28): consistent critical fields with nothing missing or contradictory; `verified` is never required. Other gates are added in their phases.

The field files are checked against `schemas/field_rules.schema.json` by the tests. Changing a rule requires re-running the evals.
