# HANDOFF

## 0. Header

- **Project:** Monkyfi Service Delivery Intelligence
- **Session:** Phase 1 — schemas, synthetic dataset and eval runner
- **Date:** 2026-11-09
- **Status:** Done. Dante approved the two examples with changes (D25–D32) and the 6-order sample with the severity table (D33).
- **Not done on purpose:** the migration has not been applied to any database, and nothing from Phase 2 was started.

## a) Summary of tasks

- [x] Review changes applied (D25–D31): handoff interface per endpoint; supplier FOC stays on the dependency; diversity without a reference is critical; G1 passes on consistency and never requires `verified`; missing-field severities accepted as defaults; every document is a PDF; every package has the full document set.
- [x] 44 synthetic orders (48 order versions, 259 PDFs with a Markdown copy each) and one golden label per version. Per product: 5 clean, 13 with one or two seeded defects, 4 adversarial. Split 24 dev / 12 eval by customer, 8 adversarial apart.
- [x] All 16 mandatory cases have test data (listed in `data/synthetic/manifest.json`).
- [x] Three simulated event files (repeated update, integration down, missing telemetry).
- [x] JSON Schemas for the 18 entities of SPEC 8.1, and one migration with tenant RLS.
- [x] Rules: interface fields per endpoint, and `rules/gates.json` with the G1 pass condition.
- [x] Eval runner with one command, reporting a denominator for every eval.
- [x] `locales/` skeleton (en, es).
- [x] `docs/PHASE1_SAMPLE.md`: 6 random orders plus the severity table, approved (D33).
- [ ] Migration executed against Postgres — not done; there is no local Postgres and applying it to Supabase needs Dante's approval.

**Tests:** `.venv/bin/python -m pytest -q` → 789 passed.

**Evals:** `.venv/bin/python evals/run.py` → exit 0. No agent exists before Phase 2, so every eval is NOT RUN and reports only its denominator. The runner's self-check passed (a perfect reference predictor passes, a blind one fails). Output for the eval split:

    SYNTHETIC — NOT REAL DATA. Thresholds on synthetic data are a development signal, not production proof.
    Split: eval — 12 orders, 13 order versions. Adversarial (reported separately): 8 orders.
    Predictions: 0 of 21 order versions (none given: no agent output exists before Phase 2)
    
    Eval                                                   Result  Threshold                         Status
    Critical field extraction                               -/828  >= 98%                            NOT RUN
    Critical field extraction (EPL)                         -/366  >= 98%                            NOT RUN
    Critical field extraction (WAVELENGTH)                  -/462  >= 98%                            NOT RUN
    Discrepancy recall (critical)                             -/6  >= 95%                            NOT RUN
    Discrepancy recall (high)                                 -/2  reported                          NOT RUN
    Discrepancy recall (medium)                               -/0  reported                          NOT RUN
    Discrepancy recall (info)                                 -/0  reported                          NOT RUN
    Discrepancy precision (overall)                             -  >= 90%                            NOT RUN  [denominator is the agent's finding count]
    Severity never lowered                                      -  0                                 NOT RUN
    Factual traceability                                        -  >= 99%                            NOT RUN  [denominator is the agent's value count]
    Invented committed dates                                 -/13  0                                 NOT RUN  [release blocker; denominator is order versions]
    Gate G1: not-ready orders passed                          -/4  0                                 NOT RUN  [release blocker]
    Gate G1: ready orders blocked                             -/9  reported                          NOT RUN
    Dates                                                    -/41  100%                              NOT RUN
    Uncertainty                                               -/8  >= 95%                            NOT RUN
    Version change                                            -/1  100%                              NOT RUN
    Segregation and embedded content (adversarial)            -/8  all                               NOT RUN  [release blocker; tenant RLS tests are added in Phase 7]
    Communication                                               -  >= 4/5 per dimension; zero leaks  NOT RUN  [manual; Phase 5]
    Integration robustness                                    -/3  all                               NOT RUN  [Phase 7; data in data/synthetic/events/]

Thresholds on synthetic data are a development signal, not production proof.

## b) Next steps for the next session

1. Dante decides whether Gemini is kept as the comparison model (D23) and approves the start of Phase 2.
2. Dante answers the open questions in section d).
3. Phase 2 (SPEC section 14): PDF reading, critical-field extraction with value, source, page, version and date, the six `field_value` statuses, and the provider layer in `src/providers/`. The agent writes `prediction.json` files that `evals/run.py --predictions DIR` scores.
4. Before any model call: confirm Meta Model API access and add the credentials to `.env` (never to the repo).

**Prompt to start the next session** (open it at the repo root, not in `docs/`):

> /prime phase 2

## c) Friction points

- **No local Postgres, Docker or Supabase CLI.** Handled: the migration is parsed with the real Postgres parser (`pglast`) and compared with the JSON Schemas by a test. Unresolved: it has never been executed, so RLS behavior is untested until it runs on a database (Phase 7 tests it with the second tenant).
- **The eval runner had two scoring bugs.** Its own self-check caught them (awaited `pending` fields with no value, and two dates on the same day in one document). Fixed; the self-check now runs on every invocation.
- **Review changes arrived after the first full generation.** Handled: rules, examples and generator were changed and the dataset regenerated; generation takes about 1.5 seconds.
- **Session working directory is `docs/`.** Every shell command needs `cd /Users/danteruiz7/monkyfi-sdi` first. Unresolved.
- **Meta Model API availability** (US-only public preview) is still untested; no credentials exist. Unresolved risk for Phase 2.

## d) Changes in the plan

Already in `docs/SPEC.md` (v1.2) and `docs/DECISIONS.md`: D25–D33.

**Choices made in this session that are not decisions (Proposed, need Dante's answer):**

- **G1 and non-critical gaps.** D28 is implemented as "a missing or contradictory field blocks G1 only when its severity is critical". Three orders therefore pass G1 with a medium or high finding: SYN-EPL-0008, SYN-WAV-0011, SYN-WAV-0017. If any missing or contradictory field should block, change `blocking_severities` in `rules/gates.json` and regenerate.
- **Demo order.** Demo step 1 needs an EPL order with 3 seeded errors; the dataset has at most 2 per order.
- **EPL fiber type and optic wavelength** were moved to the endpoint together with the interface fields (D25 named interface, optic, reach and connector).
- **A contradictory field takes the same severity as a missing one.**
- **Schema fields beyond SPEC 8.1** (listed in SPEC 8.1 "As built in Phase 1") and the database checks.
- **Supplier follow-up threshold** defaults to 5 days in the seed rows.
- **Prediction format** (`schemas/prediction.schema.json`) and locale key naming.
- **Gemini** (D23, before Phase 2).

## e) File paths

Commits on `main` (no remote): `c280c5c`, `beb2458`, `9edceef`, `7771cfe`, `c17567c`. The Phase 1 work below is in the working tree; it is committed together with this handoff.

**Documentation**

- `docs/SPEC.md` — modified. v1.2: header, section 6 (G1 rule), 8.1 (as built), 8.3, 8.4, 11.1, 11.3, 14, 17.
- `docs/DECISIONS.md` — modified. D25–D33 added.
- `docs/PHASE1_SAMPLE.md` — created. Six random orders with their documents and expected answers, plus the severity table.
- `docs/HANDOFF.md` — rewritten. This file.

**Entry points**

- `data/synthetic/generate.py` — modified. Builds orders, events and the manifest; lays out documents, writes PDF and Markdown, builds golden labels.
- `evals/run.py` — created. Eval runner.
- `data/synthetic/review_sample.py` — created. Builds `docs/PHASE1_SAMPLE.md`.
- `data/synthetic/seed.py` — created. Database rows from the dataset, written to `data/synthetic/seed/` (git-ignored).

**Modules**

- `data/synthetic/dataset.py` — created. The 44 order definitions and the mandatory-case list.
- `data/synthetic/example_orders.py` — modified. Interface values per endpoint; split set to dev.
- `data/synthetic/event_sets.py` — created. The three simulated event sets.
- `data/synthetic/pdf.py` — created. Reproducible PDF rendering with the synthetic mark on every page.

**Configuration and environment**

- `.gitignore` — modified. Ignores `data/synthetic/seed/`.
- `requirements-dev.txt` — modified. Adds `reportlab`, `pypdf`, `pglast`.
- `.env.example` — unchanged. No new variables.

**Rules**

- `rules/fields.common.json` — modified. Version 0.2.0; status text.
- `rules/fields.epl.json` — modified. Five interface fields now per endpoint.
- `rules/fields.wavelength.json` — modified. Four interface fields now per endpoint.
- `rules/gates.json` — created. G1 pass condition (D28).
- `rules/README.md` — modified.

**Schemas and migration**

- `schemas/golden_label.schema.json` — modified. Pages on sources, later gates, dependencies, version change, adversarial block.
- `schemas/simulated_event.schema.json` — created.
- `schemas/prediction.schema.json` — created.
- `schemas/README.md` — modified.
- `schemas/entities/approval.schema.json` — created. Shape of the `approval` table.
- `schemas/entities/audit_event.schema.json` — created. Shape of the `audit_event` table.
- `schemas/entities/communication.schema.json` — created. Shape of the `communication` table.
- `schemas/entities/customer.schema.json` — created. Shape of the `customer` table.
- `schemas/entities/dependency.schema.json` — created. Shape of the `dependency` table.
- `schemas/entities/document.schema.json` — created. Shape of the `document` table.
- `schemas/entities/endpoint.schema.json` — created. Shape of the `endpoint` table.
- `schemas/entities/evidence.schema.json` — created. Shape of the `evidence` table.
- `schemas/entities/field_value.schema.json` — created. Shape of the `field_value` table.
- `schemas/entities/finding.schema.json` — created. Shape of the `finding` table.
- `schemas/entities/gate_evaluation.schema.json` — created. Shape of the `gate_evaluation` table.
- `schemas/entities/milestone.schema.json` — created. Shape of the `milestone` table.
- `schemas/entities/order_version.schema.json` — created. Shape of the `order_version` table.
- `schemas/entities/project.schema.json` — created. Shape of the `project` table.
- `schemas/entities/service_order.schema.json` — created. Shape of the `service_order` table.
- `schemas/entities/shared_resource.schema.json` — created. Shape of the `shared_resource` table.
- `schemas/entities/supplier.schema.json` — created. Shape of the `supplier` table.
- `schemas/entities/tenant.schema.json` — created. Shape of the `tenant` table.
- `supabase/migrations/20261109000000_initial_schema.sql` — created. 18 tables, tenant-scoped foreign keys, RLS policies. Not executed.
- `supabase/migrations/README.md` — modified.

**Locales**

- `locales/en.json` — created.
- `locales/es.json` — created.
- `locales/README.md` — modified.

**Tests**

- `tests/conftest.py` — created. Shared paths and loaders.
- `tests/test_dataset.py` — created. Rules, composition, every order version, the G1 rule, determinism.
- `tests/test_schemas.py` — created. Entity schemas against the SQL, RLS policies, rows.
- `tests/test_evals_and_locales.py` — created. Eval scoring and locale files.
- `tests/README.md`, `evals/README.md`, `data/synthetic/README.md` — modified.

**Data** (generated by `data/synthetic/generate.py`; 566 files, indexed one by one in `data/synthetic/manifest.json` and in each `golden.json`, so they are listed here per order version)

- `data/synthetic/manifest.json` — created. Index of orders, splits and mandatory cases.
- `data/synthetic/events/repeated_update.json` — created. Case 13.
- `data/synthetic/events/integration_down.json` — created. Case 14.
- `data/synthetic/events/missing_telemetry.json` — created. Case 10.
- `data/synthetic/orders/SYN-EPL-0001/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect; cases 1, 3.
- `data/synthetic/orders/SYN-EPL-0002/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, clean.
- `data/synthetic/orders/SYN-EPL-0003/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, clean.
- `data/synthetic/orders/SYN-EPL-0004/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, clean.
- `data/synthetic/orders/SYN-EPL-0005/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect; cases 2.
- `data/synthetic/orders/SYN-EPL-0006/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect; cases 4.
- `data/synthetic/orders/SYN-EPL-0006/v2/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect; cases 4.
- `data/synthetic/orders/SYN-EPL-0007/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect; cases 8.
- `data/synthetic/orders/SYN-EPL-0007/v2/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect; cases 8.
- `data/synthetic/orders/SYN-EPL-0008/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). dev, defect; cases 5.
- `data/synthetic/orders/SYN-EPL-0009/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). dev, defect; cases 6.
- `data/synthetic/orders/SYN-EPL-0010/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect.
- `data/synthetic/orders/SYN-EPL-0011/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). dev, defect; cases 9.
- `data/synthetic/orders/SYN-EPL-0012/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect.
- `data/synthetic/orders/SYN-EPL-0013/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). eval, clean.
- `data/synthetic/orders/SYN-EPL-0014/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). eval, clean.
- `data/synthetic/orders/SYN-EPL-0015/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). eval, defect; cases 1.
- `data/synthetic/orders/SYN-EPL-0016/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). eval, defect; cases 3.
- `data/synthetic/orders/SYN-EPL-0017/v1/` — created. `golden.json`, `documents/` (7 PDFs), `markdown/` (7 copies). eval, defect; cases 15.
- `data/synthetic/orders/SYN-EPL-0018/v1/` — created. `golden.json`, `documents/` (7 PDFs), `markdown/` (7 copies). eval, defect; cases 16.
- `data/synthetic/orders/SYN-EPL-0019/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). adversarial, adversarial; cases 11.
- `data/synthetic/orders/SYN-EPL-0020/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). adversarial, adversarial; cases 11.
- `data/synthetic/orders/SYN-EPL-0021/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). adversarial, adversarial; cases 12.
- `data/synthetic/orders/SYN-EPL-0022/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). adversarial, adversarial; cases 12.
- `data/synthetic/orders/SYN-WAV-0001/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). dev, defect; cases 5, 7.
- `data/synthetic/orders/SYN-WAV-0002/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect; cases 7.
- `data/synthetic/orders/SYN-WAV-0003/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect; cases 7.
- `data/synthetic/orders/SYN-WAV-0004/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, clean.
- `data/synthetic/orders/SYN-WAV-0005/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, clean.
- `data/synthetic/orders/SYN-WAV-0006/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, clean.
- `data/synthetic/orders/SYN-WAV-0007/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect; cases 1.
- `data/synthetic/orders/SYN-WAV-0008/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect.
- `data/synthetic/orders/SYN-WAV-0009/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect; cases 8.
- `data/synthetic/orders/SYN-WAV-0009/v2/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). dev, defect; cases 8.
- `data/synthetic/orders/SYN-WAV-0010/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). dev, defect; cases 6.
- `data/synthetic/orders/SYN-WAV-0011/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). dev, defect.
- `data/synthetic/orders/SYN-WAV-0012/v1/` — created. `golden.json`, `documents/` (7 PDFs), `markdown/` (7 copies). dev, defect; cases 15, 16.
- `data/synthetic/orders/SYN-WAV-0013/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). eval, clean.
- `data/synthetic/orders/SYN-WAV-0014/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). eval, clean.
- `data/synthetic/orders/SYN-WAV-0015/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). eval, defect; cases 2.
- `data/synthetic/orders/SYN-WAV-0016/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). eval, defect; cases 4.
- `data/synthetic/orders/SYN-WAV-0016/v2/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). eval, defect; cases 4.
- `data/synthetic/orders/SYN-WAV-0017/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). eval, defect; cases 5.
- `data/synthetic/orders/SYN-WAV-0018/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). eval, defect; cases 9.
- `data/synthetic/orders/SYN-WAV-0019/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). adversarial, adversarial; cases 11.
- `data/synthetic/orders/SYN-WAV-0020/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). adversarial, adversarial; cases 11.
- `data/synthetic/orders/SYN-WAV-0021/v1/` — created. `golden.json`, `documents/` (5 PDFs), `markdown/` (5 copies). adversarial, adversarial; cases 12.
- `data/synthetic/orders/SYN-WAV-0022/v1/` — created. `golden.json`, `documents/` (6 PDFs), `markdown/` (6 copies). adversarial, adversarial; cases 12.

**Deleted**

- `data/synthetic/examples/SYN-EPL-0001/documents/01_quote.md` — deleted. Replaced by the full dataset and the new tests.
- `data/synthetic/examples/SYN-EPL-0001/documents/02_order_form_signed.md` — deleted. Replaced by the full dataset and the new tests.
- `data/synthetic/examples/SYN-EPL-0001/documents/03_technical_annex.md` — deleted. Replaced by the full dataset and the new tests.
- `data/synthetic/examples/SYN-EPL-0001/documents/04_loa_cfa.md` — deleted. Replaced by the full dataset and the new tests.
- `data/synthetic/examples/SYN-EPL-0001/documents/05_email_01.md` — deleted. Replaced by the full dataset and the new tests.
- `data/synthetic/examples/SYN-EPL-0001/golden.json` — deleted. Replaced by the full dataset and the new tests.
- `data/synthetic/examples/SYN-WAV-0001/documents/01_quote.md` — deleted. Replaced by the full dataset and the new tests.
- `data/synthetic/examples/SYN-WAV-0001/documents/02_order_form_signed.md` — deleted. Replaced by the full dataset and the new tests.
- `data/synthetic/examples/SYN-WAV-0001/documents/03_technical_annex.md` — deleted. Replaced by the full dataset and the new tests.
- `data/synthetic/examples/SYN-WAV-0001/documents/04_loa_cfa.md` — deleted. Replaced by the full dataset and the new tests.
- `data/synthetic/examples/SYN-WAV-0001/documents/05_email_01.md` — deleted. Replaced by the full dataset and the new tests.
- `data/synthetic/examples/SYN-WAV-0001/documents/06_email_02.md` — deleted. Replaced by the full dataset and the new tests.
- `data/synthetic/examples/SYN-WAV-0001/golden.json` — deleted. Replaced by the full dataset and the new tests.
- `tests/test_synthetic_examples.py` — deleted. Replaced by the full dataset and the new tests.

**Commands** (from the repo root)

- Setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`
- Regenerate the dataset: `.venv/bin/python data/synthetic/generate.py`
- Tests: `.venv/bin/python -m pytest -q`
- Evals: `.venv/bin/python evals/run.py` (add `--predictions DIR` from Phase 2)
- Review sample: `.venv/bin/python data/synthetic/review_sample.py`
- App: none yet.

## History

- Phase 0 · 2026-11-09 · Done — deliverables committed, SPEC approved (D18), amendments D19–D23 applied.
- Phase 1 · 2026-11-09 · Done — 44 orders as PDF with golden labels, 18 entity schemas, RLS migration (not executed), eval runner, locales; sample approved (D33).
