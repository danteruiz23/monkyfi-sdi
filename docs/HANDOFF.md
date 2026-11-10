# HANDOFF

## 0. Header

- **Project:** Monkyfi Service Delivery Intelligence
- **Session:** Phase 4 — milestones, dependencies, dates and gate G2 (UC04, UC05, RF04; UC07 minimal slice), plus the Phase 4 web view work
- **Date:** 2026-11-10
- **Status:** Done. Dante approved the results; exit criteria met (D69).
- **Not done on purpose:** nothing from Phase 5 was started. The database migration is still not applied anywhere (it was revised in place before any execution; D64 applies from the first execution).

## a) Summary of tasks

- [x] Step 1 (D52): "Needs action" lists every open G1 blocker, including package-level findings such as `SEG-OTHER-CUSTOMER` with document, page and value; render check fails if G1 blocks and the block is empty.
- [x] Step 2: deterministic date typing (requested / forecast / committed) from `rules/dates.json`; email dates typed from their sentence; emails never give the order a committed date (D35, D57); a firm supplier FOC stays on the dependency (D26); the tentative reading of a date wins within one email (SYN-WAV-0022). `DATE-CUSTOMER-CHANGE` finding (D57). No date without an approval record is shown as committed (D58).
- [x] Step 3: milestone plan per product (D56) with owners, applicability (unknown is never dropped), states and dates; Engineering action "Confirm on-net or off-net access", due in 2 business days (D60, D62).
- [x] Step 4: supplier dependencies, "Supplier inputs: complete / missing" (D62), follow-up counted from the last supplier email (3 / 5 business days, D55), escalation to the SDM with history, dependency graph.
- [x] Step 5: shared resources across a run (UC07): `XC-SYN-AURORA-A` is one record flagged on SYN-WAV-0001, 0002 and 0003 with one shared action.
- [x] Step 6: gate G2 (D54, D65, D67) with seeded synthetic gate records; SYN-EPL-0013 and SYN-WAV-0013 pass G1 and G2; SYN-WAV-0003 fails G2 only on the blocked shared cross-connect.
- [x] Step 7: plan section in the view, "Pending confirmation" collapsed and grouped (D50), progress with three spans and two percentages (D68).
- [x] Real Muse Spark extraction on the case 5–7 orders (D53): 40 calls, 304,066 tokens, 386/386 critical fields.
- [x] Migration revised before execution: `supplier.escalation_threshold_days`, `finding.resolving_party`.
- [x] Decisions D53–D69; SPEC v1.5; Phase 4 marked Done (D69).

**Tests:** `.venv/bin/python -m pytest -q` → 1431 passed.

**Web checks** (from `web/`): `npm run typecheck` → no errors; `npm run build` → no errors; `npm run render-check -- $(ls ../runs/phase4-view | grep SYN)` → PASS on 25 orders (36 finding renderings, 2 package-level blocker rows, 60 pages checked for unapproved commitments with 4 shown awaiting approval, 58 plan action rows incl. 6 shared-resource rows, 58 G2 cards, 58 pages with both progress numbers, 58 plan sections; English and Spanish).

**Evals** (all exit 0, scorer self-check OK):

| Eval | Eval split, Muse Spark 1.1 | Eval split, gemini-3.8-flash | Dev orders cases 1–4, 8 (D41) | Case 5–7 orders (D53) | Threshold |
|---|---|---|---|---|---|
| Critical field extraction | 828/828 | 828/828 | 564/564 | 386/386 | ≥95% |
| Discrepancy recall (critical) | 6/6 | 6/6 | 6/6 | 2/2 | ≥95% |
| Discrepancy precision | 8/8 | 8/8 | 6/6 | 3/3 | ≥90% |
| Factual traceability | 761/761 | 761/761 | — | — | ≥99% |
| G1: not-ready orders passed | 0/4 | 0/4 | 0/4 | 0/2 | 0 |
| Dates | 41/41 | 41/41 | 25/25 | 17/17 | 100% |
| Dates: no forecast or informal date as committed | 0/2 | 0/2 | 0/0 | 0/0 | 0 |
| Dates: unlabeled or mistyped mentions | 0/41 | 0/41 | 0/25 | 0/17 | reported |
| Dependencies | 1/1 | 1/1 | 0/0 | 4/4 | 100% |
| Shared resources | 13/13 | 13/13 | 9/9 | 6/6 | 100% |
| Uncertainty | 8/8 | 8/8 | — | — | ≥95% |
| Version change | 1/1 | 1/1 | — | — | 100% |

Commands: `.venv/bin/python evals/run.py --predictions runs/eval-meta` (same for `runs/eval-gemini`); `--split dev --predictions runs/dev-cases-meta`; `--split dev --predictions runs/phase4-cases-meta`. NOT RUN (later phases): adversarial, communication, integration robustness, future risk. Synthetic data; small denominators (1 labeled dependency on the eval split; cases 5–7 are mostly development orders).

**Phase 4 exit criteria**

| Criterion | Result | Evidence |
|---|---|---|
| 100% of applicable cases distinguish the three dates | PASS | Dates 41/41 (both models), 25/25, 17/17; tests match all 48 versions exactly |
| Zero forecasts or informal dates stored or shown as committed | PASS | 0/2 eval; 0 order committed dates in 43 plans; render check 0 unapproved committed displays on 60 pages (checked against a deliberately broken view) |
| Zero critical milestones without an owner | PASS | 430 critical milestones in 43 plans, 0 without owner; render check per row |
| 3-wavelength project shows the shared blocker on all 3 orders | PASS | `XC-SYN-AURORA-A` on SYN-WAV-0001/0002/0003; Shared resources 6/6 and 13/13 |
| Mandatory cases 5, 6, 7 | PASS | real Muse Spark extraction (D53); see plans in `runs/phase4-view/` |

## b) Next steps for the next session

1. Phase 5 (SPEC section 14): status per audience and approvals (UC06, RF05–RF06): the section 10 template; internal, customer and supplier drafts; audience filter; prepared / approved / sent / failed; English and Spanish from `locales/`; sending simulated. Phase 5 can reuse `plan.json` (milestones, dates by type, dependencies, follow-ups, shared resources, G2) and `validation.json`.
2. Before the demo (D66): a minimal CLI to record a human gate decision (G1 approve/override, G2 approve); the UI stays in Phase 8.
3. Backlog, in no order:
   - "Hard" synthetic subset (D39): scanned PDFs, misaligned tables, varied wording; scanned PDFs need OCR, not built.
   - Standard intervals per product in `rules/` to build a delivery forecast labeled "based on standard interval" (D61).
   - Record carrier-to-supplier requests so follow-ups count from the request, not the last supplier email (D63).
   - Phase 7: verify the supplier sender by address or domain, not only the signature line (D59); test case SYN-WAV-0022.
   - Phase 7: log every model API retry with its reason, e.g. 429 or timeout (D38).
   - Test lower reasoning effort on Muse Spark while keeping extraction ≥95% (D40); requires an eval re-run.
4. Open since Phase 3: demo order with 3 defects; applying the migration to Supabase (needs Dante's approval; after that, only new migrations, D64).

**Prompt to start the next session** (open it at the repo root, not in `docs/`):

> /prime phase 5

## c) Friction points

- **Adversarial email typed as a supplier commitment.** SYN-WAV-0022 tells the reader to record a tentative date as committed (FOC). Handled: within one email the tentative reading of a date wins. Unresolved: sender identity is read from the signature only (D59, Phase 7).
- **Render check counted Next.js script payloads.** The page text is repeated inside `<script>` tags, so label counts doubled. Handled: the check strips scripts before counting. Found by testing the check against a deliberately broken view.
- **Progress bar "as decided" was not in the repo.** The two-span decision existed only in Dante's instruction. Handled: recorded as D68 and built.
- **Preview server port.** Another session's dev server held port 3000 earlier; later it was gone and this session's preview started. Use `npx next dev -p 3001` if 3000 is taken.
- **Session working directory is `docs/`.** Every shell command needs `cd /Users/danteruiz7/monkyfi-sdi` first. Unresolved.
- **Most case 5–7 orders are development orders.** Only SYN-WAV-0017 is in the eval split; handled with a real model run (D53). Unresolved: the eval split alone cannot show cases 5–7.
- **No gate records in real life yet.** Every order without seeded records is blocked at G2. Handled: seeded synthetic records (D65). Unresolved: a CLI to record decisions (D66).
- **Shared resources need the whole folder.** Orders are linked across a run, so `src.planner.cli` must be run on the whole folder, not one order.
- **No local Postgres.** Plans, findings and gate evaluations are JSON shaped like the tables. Unchanged since Phase 1.

## d) Changes in the plan

Recorded in `docs/SPEC.md` (v1.5) and `docs/DECISIONS.md`:

- D53: cases 5–7 with real Muse Spark extraction on their development orders and SYN-WAV-0017.
- D54: basis for G2 per product.
- D55: supplier follow-up 3 business days, escalation 5, per supplier.
- D56: milestone templates per product.
- D57: amends D35 — emails may give a requested date or a forecast, never a committed date; `DATE-CUSTOMER-CHANGE` finding.
- D58: no date without an approval record is shown as committed.
- D59: Phase 7 backlog, supplier sender verification.
- D60: step 3 approved; unknown on-net/off-net creates an Engineering action.
- D61: backlog, standard intervals per product.
- D62: "Supplier inputs: complete / missing"; follow-up anchor shown; escalation history; access action due in 2 business days.
- D63: backlog, carrier-to-supplier request records.
- D64: after the first applied migration, only new migrations (in `CLAUDE.md`).
- D65: G2 rules approved with changes; seeded synthetic gate records; G2 as the G2 milestone's state.
- D66: backlog, CLI to record a human gate decision.
- D67: G2 approved.
- D68: progress with three spans and two percentages.
- D69: Phase 4 Done.

**Choices that are Proposed (not decided):** email cue words and their order (`rules/dates.json`); applicability conditions and predecessors (`rules/milestones.json`); the shared-resource reference pattern and cues (`rules/shared_resources.json`); `DATE-CUSTOMER-CHANGE` severity high; follow-up anchor = last supplier email.

**Open questions (SPEC section 17):** demo order with 3 defects; migration not applied; scoping by register misses abbreviations and misspellings; commercial model.

## e) File paths

**Entry points**

- `src/planner/cli.py` — created. Planner over a run folder: dates, milestones, dependencies, shared resources (linked across the folder), G2; writes `plan.json` and the prediction's `dates`, `dependencies`, `shared_resources`.
- `src/validators/cli.py` — modified. Reads `data/synthetic/gate_records.json` (`--gate-records`) and applies seeded G1 decisions; passes the supplier register for D57.
- `web/app/[lang]/orders/[id]/page.tsx` — modified. D52 blocker rows, workstream actions, D58 awaiting-approval badges, G2 card, two-scope progress, D50 pending block, plan section.
- `web/app/[lang]/orders/[id]/PlanSection.tsx` — created. Plan section: milestones, dependencies, shared resources, supplier inputs, delivery forecast.
- `web/app/[lang]/page.tsx` — modified. Key date and progress use `plan.json`.

**Modules**

- `src/planner/__init__.py` — created. Package docstring.
- `src/planner/dates.py` — created. Date typing from contract fields and email sentences.
- `src/planner/milestones.py` — created. Milestone plan, applicability, access-type actions.
- `src/planner/dependencies.py` — created. Supplier dependencies, follow-up, dependency graph.
- `src/planner/shared.py` — created. Shared resources across a run.
- `src/planner/g2.py` — created. G2 evaluation, access-type records, G2 milestone state.
- `src/planner/.gitkeep` — deleted.
- `src/validators/date_change.py` — created. `DATE-CUSTOMER-CHANGE` finding (D57).
- `src/validators/findings.py` — modified. Runs the date-change check when documents are given.
- `src/validators/evaluate.py` — modified. Passes the supplier register.
- `src/validators/gate.py` — modified. `record_decision` for seeded G1 approvals.
- `web/lib/data.ts` — modified. Types for plan, milestones, dependencies, shared resources, G2, actions, stage scope.
- `web/lib/model.ts` — modified. `otherBlockers`, `keyDate` with approvals, `isApprovedCommitment`, gate-aware progress with scopes, `groupFields`.
- `web/lib/config.ts` — modified. Default view folder `runs/phase4-view`.
- `web/app/globals.css` — modified. Awaiting-approval badge, span bar, D50 details, not-applicable badge.
- `web/scripts/render-check.mjs` — modified. D52, D58, actions, shared rows, G2 cards, both progress numbers, D50, plan section.

**Rules, schemas, locales, data**

- `rules/dates.json` — created. Date typing rules.
- `rules/milestones.json` — created. Milestone templates, conditions, unknown actions.
- `rules/dependencies.json` — created. Follow-up defaults and supplier inputs.
- `rules/shared_resources.json` — created. Shared-resource patterns, cues, action.
- `rules/gates.json` — modified. G2 requirements.
- `rules/findings.json` — modified. `customer_date_change`.
- `rules/stages.json` — modified. Stage scopes (D68).
- `schemas/prediction.schema.json` — modified. `dependencies`, `shared_resources`.
- `schemas/validation.schema.json` — modified. Decision `approved`, `record_id`.
- `schemas/entities/supplier.schema.json` — modified. `escalation_threshold_days`.
- `schemas/entities/finding.schema.json` — modified. `resolving_party`.
- `supabase/migrations/20261109000000_initial_schema.sql` — modified (not executed). Same two columns.
- `data/synthetic/gate_records.json` — created. 39 seeded synthetic gate records (D65).
- `data/synthetic/seed.py` — modified. Supplier thresholds 3 / 5.
- `locales/en.json`, `locales/es.json` — modified. Plan, G2, milestones, actions, progress, dates strings.

**Configuration and environment**

- `CLAUDE.md` — modified. Migration rule (D64).
- `.env.example` — modified. `SDI_VIEW_DATA_DIR` default note now `runs/phase4-view` (name only).

**Tests and evals**

- `tests/test_planner_dates.py`, `tests/test_planner_milestones.py`, `tests/test_planner_dependencies.py`, `tests/test_planner_shared.py`, `tests/test_planner_g2.py` — created.
- `evals/run.py` — modified. Date precision results, Dependencies, Shared resources; reference predictors.

**Documentation**

- `docs/SPEC.md` — modified. v1.5, Phase 4 Done, as built, backlog.
- `docs/DECISIONS.md` — modified. D53–D69.
- `docs/HANDOFF.md` — rewritten. This file.
- `rules/README.md`, `src/README.md`, `evals/README.md`, `web/README.md`, `data/synthetic/README.md`, `supabase/migrations/README.md` — modified.

**Not in the repo (git-ignored)**

- `runs/phase4-cases-meta/` — Muse Spark extraction, validation and plans of SYN-EPL-0008, 0009, SYN-WAV-0001, 0002, 0003, 0010, 0017 (log: `runs/phase4-cases-meta.log`).
- `runs/phase4-view/` — the 25 orders (29 versions) the view shows.
- `runs/eval-meta/`, `runs/eval-gemini/`, `runs/dev-cases-meta/`, `runs/adv-0019-meta/`, `runs/phase3-view/` — now also `plan.json`.
- `data/synthetic/seed/*.json` — regenerated with `python data/synthetic/seed.py`.

**Commands** (from the repo root)

- Tests: `.venv/bin/python -m pytest -q`
- Validators then planner (whole folder): `.venv/bin/python -m src.validators.cli --run runs/phase4-view --as-of 2026-11-10 --quiet` then `.venv/bin/python -m src.planner.cli --run runs/phase4-view --as-of 2026-11-10 [--show]`
- Evals: `.venv/bin/python evals/run.py --predictions runs/eval-meta`; `--split dev --predictions runs/phase4-cases-meta`
- View data: `mkdir -p runs/phase4-view && cp -R runs/eval-meta/SYN-* runs/dev-cases-meta/SYN-* runs/adv-0019-meta/SYN-* runs/phase4-cases-meta/SYN-* runs/phase4-view/`, then the validators and planner commands above
- App: `cd web && npm install && npm run dev`, then http://localhost:3000
- Web checks: `cd web && npm run typecheck && npm run build && npm run render-check -- $(ls ../runs/phase4-view | grep SYN)`

## History

- Phase 0 · 2026-11-09 · Done — deliverables committed, SPEC approved (D18), amendments D19–D23 applied.
- Phase 1 · 2026-11-09 · Done — 44 orders as PDF with golden labels, 18 entity schemas, RLS migration (not executed), eval runner, locales; sample approved (D33).
- Phase 2 · 2026-11-10 · Done — PDF/DOCX ingestion, provider layer (Muse Spark, Gemini), grounded extraction; 828/828 on the eval split on both models (D37).
- Phase 3 · 2026-11-10 · Done — validators, G1, override, version comparison, customer scoping, read-only web view; critical recall 6/6 and precision 8/8 on the eval split (D51).
- Phase 4 · 2026-11-10 · Done — date typing, milestone plan, supplier dependencies and follow-up, shared resources, G2 with seeded records, plan view; Dates 41/41, cases 5–7 with real extraction (D69).
