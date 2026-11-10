# HANDOFF

## 0. Header

- **Project:** Monkyfi Service Delivery Intelligence
- **Session:** Phase 3 — validators and gate G1 (UC02, UC03, RF02–RF03), plus the minimal read-only web view (D45)
- **Date:** 2026-11-10
- **Status:** Done. Dante accepted the results; exit criteria met (D51).
- **Not done on purpose:** nothing from Phase 4 was started. The database migration is still not applied anywhere. Of the adversarial orders, only SYN-WAV-0019 has a model run.

## a) Summary of tasks

- [x] Deterministic validators: one finding per missing or contradictory G1 field, with rule, severity, every conflicting source, internal owner, resolving party, due date and action.
- [x] Gate G1 from `rules/gates.json`: only critical findings block (D43); `verified` is never required.
- [x] Override with approver and reason; the recommendation and the original finding are kept. Severity can be lowered only by a named human with a reason.
- [x] Version comparison: only fields whose current value changed are reopened; a document carried over from an earlier version gets a "reissue" action.
- [x] Minimal customer scoping (D42): another customer of the tenant named in any document raises a critical `SEG-OTHER-CUSTOMER` finding.
- [x] Internal owner and resolving party per field (D46).
- [x] Real Muse Spark extraction on the development orders of cases 1–4 and 8 (D41).
- [x] Read-only Next.js view (D45, D47, D48): orders list, order detail, delivery progress, parallel workstreams, critical fields grouped by status; English and Spanish from `locales/`.
- [x] Decisions D41–D52 in `docs/DECISIONS.md`; `docs/SPEC.md` is v1.4.
- [x] Real Muse Spark extraction on SYN-WAV-0019: G1 block, critical `SEG-OTHER-CUSTOMER` citing `06_email_02.pdf` page 1, zero values sourced from an email; renders in the view.
- [x] Phase 3 marked Done in the SPEC (D51).
- [ ] "Needs action" listing package-level findings (D52) — first task of Phase 4.
- [ ] `resolving_party` column in the `finding` table (entity schema and migration) — noted in SPEC section 17.

**Tests:** `.venv/bin/python -m pytest -q` → 856 passed.

**Web checks** (from `web/`): `npm run typecheck` → no errors; `npm run build` → no errors; `npm run render-check -- SYN-WAV-0019 SYN-EPL-0001 SYN-WAV-0016` → PASS (10 finding renderings in English and Spanish, status counts add up, every "needs action" field links to its finding).

**Evals:** `.venv/bin/python evals/run.py --predictions runs/eval-meta` → exit 0, scorer self-check OK. Same for `runs/eval-gemini`. `--split dev --predictions runs/dev-cases-meta` → exit 0.

Synthetic data. Eval split: 12 orders, 13 order versions. Development run: 6 orders, 9 versions.

| Eval | Eval split, Muse Spark 1.1 | Eval split, gemini-3.8-flash | Development orders (D41), Muse Spark 1.1 | Threshold |
|---|---|---|---|---|
| Critical field extraction | 828/828 | 828/828 | 564/564 | ≥95% |
| Discrepancy recall (critical) | 6/6 | 6/6 | 6/6 | ≥95% |
| Discrepancy recall (high) | 2/2 | 2/2 | 0/0 | reported |
| Discrepancy precision | 8/8 | 8/8 | 6/6 | ≥90% |
| Severity lowered | 0/8 | 0/8 | 0/6 | 0 |
| Factual traceability | 761/761 | 761/761 | 510/510 | ≥99% |
| G1: not-ready orders passed | 0/4 | 0/4 | 0/4 | 0 |
| G1: ready orders blocked | 0/9 | 0/9 | 0/5 | reported |
| Uncertainty | 8/8 | 8/8 | 6/6 | ≥95% |
| Version change | 1/1 | 1/1 | 3/3 | 100% |

NOT RUN (later phases): dates, invented committed dates, adversarial, communication, integration robustness, future risk. The development model run used 45 calls and 334,828 tokens; the SYN-WAV-0019 run used 6 calls and 43,464 tokens. The adversarial eval needs the `security` section of the prediction, which is Phase 7, so SYN-WAV-0019 is checked directly on its `validation.json`, not by the eval runner.

**Phase 3 exit criteria**

| Criterion | Result | Evidence |
|---|---|---|
| Critical recall ≥95% on the eval split | PASS | 6/6 on both models |
| Overall precision ≥90% | PASS | 8/8 |
| Zero not-ready orders recommended as ready | PASS | 0/4 eval, 0/4 development |
| Zero findings on the 10 clean orders | PASS | 4 with real extraction; 10/10 in tests with a scripted model |
| On v2 only affected validations reopened | PASS | 1/1 eval, 3/3 development |
| Mandatory cases 1, 2, 3, 4, 8 | PASS | all with real extraction |
| SYN-WAV-0019 blocked at G1 (D42) | PASS | real Muse Spark extraction (`runs/adv-0019-meta/`) and tests |
| SYN-EPL-0001 and SYN-WAV-0016 render with all findings (D45) | PASS | `npm run render-check`; SYN-WAV-0019 renders too |

Thresholds on synthetic data are a development signal, not production proof. The denominators are small: one missed critical finding on the eval split would give 83%.

## b) Next steps for the next session

1. First task of Phase 4 (D52): "Needs action" in `web/app/[lang]/orders/[id]/page.tsx` lists everything that blocks G1, including package-level findings such as `SEG-OTHER-CUSTOMER` with their document and page. Add to `web/scripts/render-check.mjs`: if G1 recommends block, "Needs action" is not empty. Check it on SYN-WAV-0019 (`runs/adv-0019-meta/`).
1. Phase 4 (SPEC section 14): milestone plan with owners, dependency graph, requested / forecast / committed dates, supplier follow-up threshold, *not estimable*, G2, and a blocked `shared_resource` flagging all linked orders. Exit: mandatory cases 5, 6 and 7.
2. Phase 4 web view backlog (D50): collapse the "Pending confirmation" block by default and group it by field group with a count per group.
3. Phase 4 can reuse: `version_change.plan_impact_fields` in `validation.json` (which changed fields may move milestones) and `observations` in `extraction.json` (what emails say; emails are forecast evidence only, D35).
4. Add `resolving_party` to `schemas/entities/finding.schema.json` and the migration together.
5. Backlog unchanged: D38 (retry logging, Phase 7), D39 (hard synthetic subset), D40 (lower reasoning effort).

**Prompt to start the next session** (open it at the repo root, not in `docs/`):

> /prime phase 4

## c) Friction points

- **Case 8 had no eval-split order.** Its orders are development orders. Handled: Dante approved a model run on them (D41). Unresolved: the eval split still cannot show case 8 by itself.
- **SYN-WAV-0019 first proven only with a scripted model.** Handled: Dante asked for a real run on that order; it passed. Unresolved: the other 7 adversarial orders have no model run (Phase 7).
- **"Needs action" can be empty on a blocked order.** In SYN-WAV-0019 the only finding is on `customer_name`, whose field status is pending, so the panel shows 0 fields needing action while G1 blocks. The finding itself is shown above. Decided (D52): fix it as the first task of Phase 4.
- **GitHub remote.** Handled: `origin` is a private GitHub repository, pushed at 32fc37c (checked with `git remote -v` in the Phase 4 session).
- **The view cannot record a human decision.** Every order shows "Order received", 1 of 11 stages. Unresolved by design: recording decisions from the UI is Phase 8.
- **Key date is almost always "requested".** Forecast and committed dates are printed as "To be confirmed" in most orders. Not a defect; Phase 4 adds forecasts.
- **Preview launcher location.** The session's working directory is `docs/`, so the app's preview needed `docs/.claude/launch.json`. Handled: the file is git-ignored. `.gitignore` also ignores `next-env.d.ts`.
- **Port 3000 in use.** The session's preview server holds it; a second `npm run dev` fails with EADDRINUSE. Use `npx next dev -p 3001` or stop the first.
- **Session working directory is `docs/`.** Every shell command needs `cd /Users/danteruiz7/monkyfi-sdi` first. Unresolved.
- **No local Postgres.** Findings and gate evaluations are JSON shaped like the tables. Unresolved, unchanged since Phase 1.

## d) Changes in the plan

Recorded in `docs/SPEC.md` (v1.4) and `docs/DECISIONS.md`:

- D41: case 8 shown with real extraction on development orders.
- D42: minimal customer scoping pulled into Phase 3; full adversarial defense stays in Phase 7.
- D43: only critical findings block G1. Closes the open item in SPEC section 17.
- D44: due dates accepted as proposals (business days: critical 1, high 2, medium 5, info 10).
- D45: minimal read-only web view pulled forward from Phase 8; Next.js decided; new exit criterion.
- D46: internal owner and resolving party per finding.
- D47: view layout approved; Presales shown as assumed complete (1 of 11).
- D48: critical fields panel grouped by status.
- D49: a field printed as "To be confirmed" goes under "Not applicable or not set".
- D50: Phase 4 backlog for the "Pending confirmation" block.
- D51: Phase 3 Done.
- D52: "Needs action" lists everything that blocks G1; first task of Phase 4.

**Choices made in this session that are not decisions (Proposed):**

- A contradictory field takes the severity of a missing one (already Proposed in SPEC 8.3).
- Impact is "confirmed" when the finding blocks the gate, "possible" otherwise.
- Which changed fields may affect the plan (`rules/findings.json`, `version_change.plan_affecting`).
- `acceptance.deemed_acceptance_period` follows the deemed-acceptance clause to Sales (D46 names only the clause).
- Customer register in `data/synthetic/customers.json` as the stand-in for the `customer` table; names matched as whole words, case-insensitive, with or without the synthetic suffix.
- Key date on screen: committed if stated, else forecast, else requested, always with its type.
- No i18n library in the view: it reads `locales/*.json` directly.

**Open questions (SPEC section 17):** demo order with 3 defects; migration not applied; `resolving_party` column; scoping by register misses abbreviations and misspellings; commercial model.

## e) File paths

**Entry points**

- `src/validators/cli.py` — created. Validators and G1 over an extraction run; writes `validation.json`, adds findings, gate and reopened validations to `prediction.json`.
- `web/app/[lang]/page.tsx` — created. Orders list.
- `web/app/[lang]/orders/[id]/page.tsx` — created. Order detail: progress, workstreams, G1 requirements, findings, version changes, critical fields by status.
- `web/app/[lang]/layout.tsx` — created. Synthetic mark on every screen, language switch.

**Modules**

- `src/validators/__init__.py` — created. Package exports.
- `src/validators/rules.py` — created. Loads `rules/findings.json`, `gates.json`, `severity.json`; severity rank.
- `src/validators/findings.py` — created. Findings, owners (`parties`), business-day due dates, `lower_severity`.
- `src/validators/gate.py` — created. `evaluate_g1`, `override_gate`.
- `src/validators/versions.py` — created. `compare_versions`, `carry_verifications`, `finding_changes`.
- `src/validators/segregation.py` — created. Customer scoping (D42).
- `src/validators/evaluate.py` — created. Validation record, projection to the prediction, `render_finding`.
- `src/i18n.py` — created. Text from `locales/` by key and parameters.
- `web/lib/config.ts` — created. Repo paths and the run folder.
- `web/lib/data.ts` — created. Reads run files and rules; types.
- `web/lib/model.ts` — created. Key date, progress, requirements, field buckets.
- `web/lib/i18n.ts` — created. Translator; a missing key is an error.
- `web/lib/ui.tsx` — created. Severity and gate badges, severity counts.
- `web/app/globals.css` — created. Styles, light and dark.
- `web/scripts/render-check.mjs` — created. Starts the built view and checks findings and the fields panel against the run files.

**Rules, schemas, locales, data**

- `rules/findings.json` — created. Finding rules, owners (D46), due dates (D44), customer scoping (D42), plan-affecting fields.
- `rules/stages.json` — created. The 11 stages, equal weights, exit gates, Presales assumption (D47).
- `schemas/validation.schema.json` — created. Shape of `validation.json`.
- `locales/en.json`, `locales/es.json` — modified. Finding rules and actions, owner roles, finding status, impact, stages, field groups, view strings.
- `data/synthetic/customers.json` — created. Customer register of the synthetic tenant.

**Configuration and environment**

- `.env.example` — modified. Adds `SDI_VIEW_DATA_DIR` (name only).
- `.gitignore` — modified. Ignores `**/.claude/launch.json` and `next-env.d.ts`.
- `web/package.json` — created. Next.js 16.4.6, React 19.3.1, scripts `dev`, `build`, `start`, `typecheck`, `render-check`.
- `web/package-lock.json` — created. Locked dependencies.
- `web/tsconfig.json` — created. TypeScript settings.
- `web/next.config.mjs` — created. Redirect `/` → `/en`; reads only `SDI_VIEW_DATA_DIR` from the repo's `.env`.

**Tests**

- `tests/test_validators.py` — created. Findings and gate against all 48 labels, owners, scoping, override, version change, mandatory cases, CLI, locales.
- `tests/test_web_view.py` — created. No hardcoded strings, locale keys exist, stage rules, read-only.

**Documentation**

- `docs/SPEC.md` — modified. v1.4: D41–D51, Phase 3 Done, Phase 3 deliverables, exit criteria, status and as-built, section 17.
- `docs/DECISIONS.md` — modified. D41–D52.
- `docs/HANDOFF.md` — rewritten. This file.
- `src/README.md`, `rules/README.md`, `evals/README.md`, `web/README.md` — modified. Phase 3 code and commands.

**Not in the repo (git-ignored)**

- `runs/eval-meta/`, `runs/eval-gemini/` — now also `validation.json` per order version.
- `runs/dev-cases-meta/` — Muse Spark extraction and validation of SYN-EPL-0001, 0005, 0006, 0007 and SYN-WAV-0007, 0009.
- `runs/adv-0019-meta/` — Muse Spark extraction and validation of SYN-WAV-0019.
- `runs/phase3-view/` — the 19 orders the view shows, copied from `runs/eval-meta/`, `runs/dev-cases-meta/` and `runs/adv-0019-meta/`.
- `docs/.claude/launch.json` — preview launcher for the session.
- `web/node_modules/`, `web/.next/`.

**Commands** (from the repo root)

- Tests: `.venv/bin/python -m pytest -q`
- Validators: `.venv/bin/python -m src.validators.cli --run runs/eval-meta` (add `--language es`, `--as-of YYYY-MM-DD`, `--quiet`)
- Evals: `.venv/bin/python evals/run.py --predictions runs/eval-meta`
- Development cases: `.venv/bin/python evals/run.py --split dev --predictions runs/dev-cases-meta`
- View data: `mkdir -p runs/phase3-view && cp -R runs/eval-meta/SYN-* runs/dev-cases-meta/SYN-* runs/adv-0019-meta/SYN-* runs/phase3-view/`
- App: `cd web && npm install && npm run dev`, then http://localhost:3000
- Web checks: `cd web && npm run typecheck && npm run build && npm run render-check`

## History

- Phase 0 · 2026-11-09 · Done — deliverables committed, SPEC approved (D18), amendments D19–D23 applied.
- Phase 1 · 2026-11-09 · Done — 44 orders as PDF with golden labels, 18 entity schemas, RLS migration (not executed), eval runner, locales; sample approved (D33).
- Phase 2 · 2026-11-10 · Done — PDF/DOCX ingestion, provider layer (Muse Spark, Gemini), grounded extraction; 828/828 on the eval split on both models (D37).
- Phase 3 · 2026-11-10 · Done — validators, G1, override, version comparison, customer scoping, read-only web view; critical recall 6/6 and precision 8/8 on the eval split (D51).
