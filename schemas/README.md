# schemas

JSON Schema (draft 2020-12).

- `entities/<table>.schema.json` — one per entity in SPEC 8.1 (18 tables). Each must agree with the SQL in `supabase/migrations/`; `tests/test_schemas.py` checks columns, types, nullability and allowed values.
- `field_rules.schema.json` — shape of the `rules/fields.*.json` files.
- `golden_label.schema.json` — shape of each order version's `golden.json`.
- `simulated_event.schema.json` — shape of `data/synthetic/events/*.json`.
- `prediction.schema.json` — the agent output that `evals/run.py` scores (Proposed; refined in Phases 2–3).
