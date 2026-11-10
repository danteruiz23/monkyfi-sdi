# HANDOFF

## 0. Header

- **Project:** Monkyfi Service Delivery Intelligence
- **Phase:** 0 · SPEC, decisions and repository
- **Date:** 2026-11-09
- **Status:** Done — all deliverables are committed and Dante approved `docs/SPEC.md` on 2026-11-09 (D18).

## a) Summary of tasks

- [x] Read the PRD, the review and the definitions; raised 9 contradictions; Dante accepted all 9 recommendations (D09–D17).
- [x] Renamed the three source documents to stable names, content unchanged.
- [x] Created the repository structure (READMEs and `.gitkeep` only).
- [x] Wrote `docs/SPEC.md`.
- [x] Wrote `CLAUDE.md`.
- [x] Wrote `docs/DECISIONS.md` (D01–D17, dated 2026-11-09).
- [x] Wrote `.gitignore` and `.env.example` (names only).
- [x] Committed (`c280c5c`, branch `main`, no remote configured).
- [x] Dante approved `docs/SPEC.md`.

**Tests / build:** none exist yet; there is no product code. Checks run: `grep -n -i "google" docs/SPEC.md docs/DECISIONS.md CLAUDE.md` returned no matches (no real prospect name in the new docs). No evals exist until Phase 1.

## b) Next steps for the next session

1. Dante approves starting Phase 1 (approval of the SPEC is not approval to start the next phase).
2. Dante validates the items in SPEC section 17 that Phase 1 depends on: critical fields (8.4), default severity (8.3), demo script (3.3).
3. Confirm whether Gemini stays as the comparison model (see section d).
4. After approval, start Phase 1: JSON Schemas, Supabase migrations with RLS, EPL and wavelength rules, the 44 synthetic orders with golden labels, simulated events, eval runner.

**Prompt to start the next session:**

> Run /prime phase 1. When I approve the plan, build only Phase 1 as described in docs/SPEC.md, run tests and evals, and finish with /hand-off.

## c) Friction points

- **Source file names.** The prompt referenced `docs/PRD.md`, `docs/REVIEW.md` and `docs/DEFINITIONS.md`, but the files had their Spanish export names. Handled: renamed with approval (D09). Resolved.
- **Session working directory is `docs/`, not the repo root.** Shell commands must `cd /Users/danteruiz7/monkyfi-sdi` first. Unresolved; open the next session at the repo root.
- **Embedded chart missing from the review.** `docs/REVIEW.md` line 66 has an "embedded content" placeholder for the phase plan. The phase text below it was complete, so nothing was lost that I could detect.
- **Source documents disagreed in 9 places** (UC07 in the demo, Phase 6 scope, G0/G2, dataset size, missing entities, segregation level, and others). Handled by asking; all resolved in D09–D17.
- **Meta Model API availability.** The review notes it is in public preview in the US only. Not tested this phase; no credentials exist yet. Unresolved risk for Phase 2.

## d) Changes in the plan

All of these are already in `docs/SPEC.md` and `docs/DECISIONS.md`.

- Phase 3 covers G1 only; G2 moved to Phase 4; G0 is post-demo (D13).
- Phase 6 is UC08 with G3–G4 only; UC09, UC10 and G5 are post-demo (D12).
- Phase 4 includes a minimal UC07 slice (D11).
- Dataset total is 44 orders: 36 in the split plus 8 adversarial (D14).
- Schema adds `evidence` and `supplier` (D15); two-level segregation with a second synthetic tenant (D16).
- Extra folders: `web/`, `supabase/migrations/`, `locales/`, `prompts/`, `src/providers/` (D10).
- Proposed, not decided: table `order` renamed `service_order` (reserved word in Postgres); Phase 2 threshold of ≥95% critical-field accuracy on the synthetic eval split; added measurable exit criteria to every phase.

**Open questions for Dante:**

- Mid-session message: "the model to use would be muse meta API". Recorded as confirming D06 (Muse Spark 1.1 is the agent model). Should Gemini remain as the comparison model, or be removed?
- The other open decisions are listed in SPEC section 17.

## e) File paths

**Documentation**

- `docs/SPEC.md` — created. Source of truth: adjusted PRD, glossary, scope, data plan, schema, 16 cases, phases 0–8.
- `docs/DECISIONS.md` — created. Decision log D01–D17.
- `docs/HANDOFF.md` — created. This file.
- `docs/PRD.md` — renamed from `docs/Monkyfi_Service_Delivery_PRD.md`. Original PRD v0.1, Spanish, unchanged.
- `docs/REVIEW.md` — renamed from `docs/Monkyfi SDI — Revisión del PRD y plan de construcción por fases.md`. Unchanged content; file mode set to 644.
- `docs/DEFINITIONS.md` — renamed from `docs/Definiciones críticas.md`. Unchanged.

**Configuration and environment**

- `CLAUDE.md` — created. Permanent rules for every session.
- `.gitignore` — created. Ignores `.env`, keys, real-data folders, Python/Node/Supabase artifacts.
- `.env.example` — created. Names only: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL`, `MODEL_PROVIDER`, `META_MODEL_API_KEY`, `META_MODEL_API_BASE_URL`, `META_MODEL_NAME`, `GEMINI_API_KEY`, `GEMINI_MODEL_NAME`, `DEFAULT_LANGUAGE`, `DEFAULT_TIMEZONE`.

**Modules (placeholders only)**

- `src/README.md` — created.
- `src/ingest/.gitkeep`, `src/validators/.gitkeep`, `src/planner/.gitkeep`, `src/comms/.gitkeep`, `src/acceptance/.gitkeep`, `src/audit/.gitkeep`, `src/providers/.gitkeep` — created, empty.
- `web/README.md` — created.
- `prompts/README.md` — created.
- `locales/README.md` — created.

**Data and schema (placeholders only)**

- `schemas/README.md` — created.
- `rules/README.md` — created.
- `data/synthetic/README.md` — created.
- `supabase/migrations/README.md` — created.

**Tests and evals (placeholders only)**

- `evals/README.md` — created.
- `tests/README.md` — created.

**Commands:** there is no app, test or eval command yet. Phase 1 delivers the single-command eval runner.

## History

- Phase 0 · 2026-11-09 · Done — deliverables committed, SPEC approved.
