# HANDOFF

## 0. Header

- **Project:** Monkyfi Service Delivery Intelligence
- **Session:** Phase 0 session (ran over into Phase 1 by mistake)
- **Date:** 2026-11-09
- **Phase 0:** Done — SPEC approved (D18); amendments D19–D23 applied as SPEC v1.1.
- **Phase 1:** Partially done — started in this session because the amendment message, which also said "build Phase 1", was pasted here by mistake. Stopped on Dante's instruction. Exactly what exists is listed in section a) and e). Nothing was built after the stop.

## a) Summary of tasks

**Phase 0 (Done)**

- [x] Read the PRD, the review and the definitions; raised 9 contradictions; all 9 recommendations accepted (D09–D17).
- [x] Source documents renamed to `docs/PRD.md`, `docs/REVIEW.md`, `docs/DEFINITIONS.md`, content unchanged.
- [x] Repository structure, `docs/SPEC.md`, `CLAUDE.md`, `docs/DECISIONS.md`, `.gitignore`, `.env.example`.
- [x] SPEC approved by Dante (D18).
- [x] SPEC amendments applied (v1.1): critical fields validated with additions (D19), severity validated with changes (D20), two demo variants (D21), `service_order_id` foreign keys (D22), Gemini stays Proposed until before Phase 2 (D23). D24 records the instruction to start Phase 1 and review two examples first.

**Phase 1 (Partially done — built before the stop)**

- [x] Critical-field rules as JSON for common, EPL and wavelength fields.
- [x] Severity rules and label synonyms (including FOC date = committed date) as JSON.
- [x] JSON Schemas for the rules files and for the golden label.
- [x] Synthetic generator and the specs of two example orders.
- [x] Two generated example orders: `SYN-EPL-0001` and `SYN-WAV-0001` (documents in Markdown plus `golden.json`).
- [x] Checks on the rules and the examples.
- [ ] Dante's review of the two example orders (he answered "Yes, generate rest", then stopped the session; treat the review as not confirmed until the Phase 1 session).
- [ ] JSON Schemas for the entities in SPEC 8.1.
- [ ] Supabase migrations with RLS.
- [ ] The remaining 42 orders (44 total), the other 2 Project Aurora circuits, v1/v2 orders, adversarial orders.
- [ ] Simulated event files.
- [ ] Eval runner with a single command.
- [ ] `locales/` skeleton (en, es).
- [ ] PDF rendering of documents (Proposed).

**Tests:** `.venv/bin/python -m pytest -q` → 23 passed. No evals exist yet (the eval runner is not built).

## b) Next steps for the next session

1. Run `/prime phase 1` and review the brief. Decide whether to keep, change or discard the Phase 1 work listed in section e).
2. Confirm or correct the two example orders, and the open questions in section d).
3. Continue Phase 1 from SPEC section 14: generate the rest of the dataset, entity schemas, migrations with RLS, simulated events, eval runner, `locales/` skeleton.
4. Dante reviews a sample of 6 orders before Phase 1 closes.

**Prompt to start the next session** (open it at the repo root, not in `docs/`):

> /prime phase 1

## c) Friction points

- **Amendments pasted in the wrong session.** The message said "then build Phase 1", so Phase 1 work started here. Handled: stopped on instruction, work committed and listed. Unresolved: the next session must decide whether to keep it.
- **First amendment message arrived truncated.** Handled: asked for a resend before changing anything. Resolved.
- **No Python packages installed.** `jsonschema` and `pytest` were missing. Handled: created `.venv` (git-ignored) and `requirements-dev.txt`. `reportlab` is not installed, so documents are Markdown, not PDF. Unresolved: PDF rendering.
- **Session working directory is `docs/`.** Every shell command needs `cd /Users/danteruiz7/monkyfi-sdi` first. Unresolved.
- **Meta Model API availability** (US-only public preview per the review) is untested; no credentials exist. Unresolved risk for Phase 2.

## d) Changes in the plan

Already in `docs/SPEC.md` (v1.1) and `docs/DECISIONS.md`: D19–D24.

**Choices made in the Phase 1 work that are not decisions (Proposed, need Dante's answer):**

- A supplier's FOC date: should it stay on the supplier dependency, or map to the order's committed date like a carrier FOC?
- "Route diversity without a reference" is rated critical (tie-break rule applied).
- Consistent extracted values are labeled `pending`; `verified` is reserved for the data owner.
- `missing_severity` and `authoritative_source` per field in `rules/fields.*.json` are defaults.
- Interface fields are stored once per order, not per end.
- Documents are Markdown; PDF rendering deferred.
- Whether Gemini is kept (D23, before Phase 2).

## e) File paths

Commits on `main` (no remote): `c280c5c`, `beb2458`, `9edceef` (Phase 0); `7771cfe` (amendments + Phase 1 partial); plus the commit containing this handoff.

**Documentation**

- `docs/SPEC.md` — modified. v1.1: sections 1, 3.3, 7.2, 8.1, 8.3, 8.4, 11.3, 14 (Phase 2), 17, header and labels.
- `docs/DECISIONS.md` — modified. D18–D24 added; rows sorted D01–D24.
- `docs/HANDOFF.md` — rewritten. This file.
- `docs/PRD.md`, `docs/REVIEW.md`, `docs/DEFINITIONS.md` — renamed in Phase 0, unchanged since.
- `CLAUDE.md` — created in Phase 0, unchanged since.

**Configuration and environment**

- `.gitignore`, `.env.example` — created in Phase 0, unchanged since. Variable names: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL`, `MODEL_PROVIDER`, `META_MODEL_API_KEY`, `META_MODEL_API_BASE_URL`, `META_MODEL_NAME`, `GEMINI_API_KEY`, `GEMINI_MODEL_NAME`, `DEFAULT_LANGUAGE`, `DEFAULT_TIMEZONE`.
- `requirements-dev.txt` — created (Phase 1). `jsonschema`, `pytest`.

**Rules (Phase 1)**

- `rules/fields.common.json` — created. Critical fields for both products.
- `rules/fields.epl.json` — created. EPL-only fields.
- `rules/fields.wavelength.json` — created. Wavelength-only fields.
- `rules/severity.json` — created. Levels, always-critical cases, tie-break.
- `rules/synonyms.json` — created. Label synonyms for extraction.
- `rules/README.md` — modified. Describes the files above.

**Schemas (Phase 1)**

- `schemas/field_rules.schema.json` — created. Shape of `rules/fields.*.json`.
- `schemas/golden_label.schema.json` — created. Shape of each `golden.json`.
- `schemas/README.md` — modified.

**Data and generator (Phase 1)**

- `data/synthetic/generate.py` — created. Builds documents and golden labels from a truth plus seeded defects.
- `data/synthetic/example_orders.py` — created. Specs of the two example orders.
- `data/synthetic/README.md` — modified.
- `data/synthetic/examples/SYN-EPL-0001/golden.json` — created.
- `data/synthetic/examples/SYN-EPL-0001/documents/01_quote.md` — created.
- `data/synthetic/examples/SYN-EPL-0001/documents/02_order_form_signed.md` — created.
- `data/synthetic/examples/SYN-EPL-0001/documents/03_technical_annex.md` — created.
- `data/synthetic/examples/SYN-EPL-0001/documents/04_loa_cfa.md` — created.
- `data/synthetic/examples/SYN-EPL-0001/documents/05_email_01.md` — created.
- `data/synthetic/examples/SYN-WAV-0001/golden.json` — created.
- `data/synthetic/examples/SYN-WAV-0001/documents/01_quote.md` — created.
- `data/synthetic/examples/SYN-WAV-0001/documents/02_order_form_signed.md` — created.
- `data/synthetic/examples/SYN-WAV-0001/documents/03_technical_annex.md` — created.
- `data/synthetic/examples/SYN-WAV-0001/documents/04_loa_cfa.md` — created.
- `data/synthetic/examples/SYN-WAV-0001/documents/05_email_01.md` — created.
- `data/synthetic/examples/SYN-WAV-0001/documents/06_email_02.md` — created.

**Tests (Phase 1)**

- `tests/test_synthetic_examples.py` — created. 23 checks: schema validity, synthetic mark, no real company names, one label per critical field, no value without a source, gate logic, no invented committed date, deterministic generation.

**Placeholders from Phase 0, unchanged:** `src/README.md`, `src/ingest/.gitkeep`, `src/validators/.gitkeep`, `src/planner/.gitkeep`, `src/comms/.gitkeep`, `src/acceptance/.gitkeep`, `src/audit/.gitkeep`, `src/providers/.gitkeep`, `web/README.md`, `prompts/README.md`, `locales/README.md`, `supabase/migrations/README.md`, `evals/README.md`, `tests/README.md`.

**Commands** (from the repo root)

- Setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`
- Regenerate examples: `.venv/bin/python data/synthetic/generate.py`
- Tests: `.venv/bin/python -m pytest -q`
- App and evals: none yet.

## History

- Phase 0 · 2026-11-09 · Done — deliverables committed, SPEC approved (D18), amendments D19–D23 applied.
- Phase 1 · 2026-11-09 · Partially done — rules, two schemas, generator and two example orders; stopped on instruction.
