# src

Python package: ingestion, extraction, validators, planner, comms, acceptance, audit and the model provider layer. Run modules from the repo root (`.venv/bin/python -m src.<module>`).

Built so far (Phases 2–3):

- `ingest/` — reads PDF (pypdf) and DOCX (no extra dependency) page by page, with file hash, document type from the title (`rules/extraction.json`) and ingestion time. No OCR.
- `providers/` — one interface for every model call. `meta` is Muse Spark 1.1 via Meta Model API (OpenAI-compatible). Answers are validated against a JSON Schema with bounded retries, recorded in `runs/recordings/` and can be replayed offline. `fake.py` is for tests only. `gemini` is gemini-3.8-flash, the comparison model (D36).
- `extract/` — critical-field extraction. The model proposes mentions per document; deterministic code grounds them (the text must be printed on the cited page), normalizes them and sets the status of each field across documents.
- `validators/` — Phase 3, deterministic, no model call. Findings for every missing or contradictory G1 field (rule, severity, sources, internal owner, resolving party, due date, action), the G1 recommendation, the human override (reason and approver; the finding stays) and the comparison with the previous order version (only changed fields are reopened). Minimal customer scoping (D42): a document that names another customer of the tenant raises a critical `SEG-OTHER-CUSTOMER` finding; the register is `data/synthetic/customers.json`. Rules in `rules/findings.json` and `rules/gates.json`.
- `i18n.py` — user-facing text from `locales/`; code keeps a key and its parameters.

Run:

    .venv/bin/python -m src.extract.cli --split eval --out runs/eval-latest   # needs .env
    .venv/bin/python -m src.extract.cli --split eval --out runs/eval-latest --replay
    .venv/bin/python -m src.validators.cli --run runs/eval-latest                 # findings and G1; add --language es
    .venv/bin/python evals/run.py --predictions runs/eval-latest

Empty until their phase: `planner/`, `comms/`, `acceptance/`, `audit/`. See `docs/SPEC.md`.

## Phase 4: planner

- `src/planner/dates.py` — deterministic date typing (rules in `rules/dates.json`). Reads the grounded quote and order-form dates from `extraction.json` and the email page text directly; the model's field keys are not used. Output: the `dates` section of `plan.json` (typed mentions with sentence and assumptions, ignored mentions with reason, and the order's dates by type) and the `dates` section of `prediction.json`.
- `src/planner/milestones.py` — milestone plan per product from `rules/milestones.json` (D56): owner, applicability (applies / not applicable / unknown), state (the intake milestone follows G1), requested date on delivery (signed order form), forecast only from dated evidence with its assumptions (a supplier's date on the supplier milestone), committed date only with an approval record; everything else `not_estimable`.
- `src/planner/dependencies.py` — supplier dependencies from registered-supplier emails: date and type (D26), estimability, follow-up schedule and state (D55), and the dependency graph. The CLI adds follow-up actions (owner Supplier Management, escalation to the SDM) and the order forecast status.
- `src/planner/shared.py` — shared resources across a run (UC07): one record per reference, linked to every affected order (also orders not in the run), blocked state from the latest email, one shared action; a blocked resource blocks the linked milestone on every order.
- `src/planner/cli.py` — `.venv/bin/python -m src.planner.cli --run runs/eval-meta [--orders ...] [--as-of YYYY-MM-DD] [--show]`. Run after the validators.
