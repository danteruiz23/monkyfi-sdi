# rules

Rules as JSON, readable by Python and TypeScript.

- `fields.common.json`, `fields.epl.json`, `fields.wavelength.json` — critical fields per product (SPEC 8.4, validated: D19). `authoritative_source` and `missing_severity` are Proposed defaults.
- `severity.json` — severity levels and the tie-break rule (SPEC 8.3, validated: D20).
- `synonyms.json` — label synonyms for extraction, including FOC date = committed date (D19).

Gate rules are added in Phase 3. The files are checked against `schemas/field_rules.schema.json` by the tests.
