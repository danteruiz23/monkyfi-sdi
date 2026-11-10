# web

Read-only web view (Phase 3, D45 and D47): Next.js and TypeScript. It reads the local run files and
calls nothing: no database, no model, no sending, no write. SYNTHETIC — NOT REAL DATA.

## What it shows

- `/en` (or `/es`) — orders list: order ID, customer, service, stage, G1 recommendation, finding
  counts by severity, and the key date with its type (requested, forecast or committed).
- `/en/orders/<order id>?v=<N>` — order detail: delivery progress, parallel workstreams, G1 with met
  and unmet requirements, findings (every conflicting value with its document and page, internal
  owner, resolving party, due date and action), changes from the previous version, critical fields.

Delivery progress is completed stages ÷ 11, with equal weights from `rules/stages.json`. Presales is
shown as assumed complete because the order is signed and no G0 record exists (D47). A stage with a
gate is completed only by a human decision, so an order stays in "Order received" until someone
passes G1. Open findings are parallel work and do not change the percentage.

## Run

From the repo root:

    mkdir -p runs/phase4-view && cp -R runs/eval-meta/SYN-* runs/dev-cases-meta/SYN-* \
        runs/adv-0019-meta/SYN-* runs/phase4-cases-meta/SYN-* runs/phase4-view/
    .venv/bin/python -m src.validators.cli --run runs/phase4-view --as-of 2026-11-10   # validation.json
    .venv/bin/python -m src.planner.cli --run runs/phase4-view --as-of 2026-11-10      # plan.json (links orders across the folder)
    cd web && npm install && npm run dev                             # http://localhost:3000

The folder shown is `SDI_VIEW_DATA_DIR` in `.env` (relative to the repo root); when it is empty the
view reads `runs/phase4-view`. Shared resources are linked across the orders of the folder, so plan the
whole folder at once.

## Checks

    cd web && npm run typecheck
    cd web && npm run build && npm run render-check    # SYN-EPL-0001 and SYN-WAV-0016, all findings, en and es
    .venv/bin/python -m pytest -q tests/test_web_view.py   # no hardcoded strings; locale keys exist

Every user-facing string comes from `locales/` (`lib/i18n.ts`); a missing key is an error. Field keys,
file names and rule ids are data and are shown as they are. The view runs locally only; deployment
on Vercel and the rest of the web view are Phase 8.

## Phase 4 view

Order detail adds, in this order: delivery progress as one line with three spans (Before / Service delivery — SDM scope / After) with the service delivery percentage first and end to end second (D68); the G2 card; the plan (milestones, dependencies, shared resources, supplier inputs, delivery forecast); the critical fields panel with "Pending confirmation" collapsed and grouped by field group (D50). `npm run render-check` checks all of it against `plan.json`, `validation.json` and `extraction.json`, in English and Spanish.
