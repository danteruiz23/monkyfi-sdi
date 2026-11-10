# data/synthetic

Synthetic orders, documents, golden labels and simulated events. Everything here is **SYNTHETIC — NOT REAL DATA**: companies, people, addresses and identifiers are fictional, and no real company names are used.

**Contents**

- `orders/<order id>/v<N>/documents/*.pdf` — the order package for that version: quote, signed order form, technical annex, LOA-CFA when a cross-connect is needed, 1–3 emails, and a test report where delivery is tested. The PDFs are the documents of record; Phase 2 extraction is evaluated on them (D30).
- `orders/<order id>/v<N>/markdown/*.md` — the same documents as Markdown, for review and diffs only.
- `orders/<order id>/v<N>/golden.json` — the expected answers: fields with source document, page and location; findings; G1 recommendation; date types; and, where they apply, dependencies, version changes, G3/G4 recommendations and adversarial content.
- `events/*.json` — simulated event files (repeated update, integration down, missing telemetry).
- `manifest.json` — index of orders, splits and the 16 mandatory cases.

**Composition (SPEC 11.1):** 44 orders — per product 5 clean, 13 with one or two seeded defects, 4 adversarial. Split: 24 development and 12 evaluation, separated by customer; the 8 adversarial orders are reported separately. Four orders have two versions.

**Code**

- `generate.py` — builds each order from a "truth" plus seeded defects, so the golden label is known by construction.
- `dataset.py` — the 44 order definitions. `example_orders.py` holds the two hand-written orders reviewed first (D24, D32).
- `event_sets.py` — the simulated events.
- `pdf.py` — PDF rendering (reproducible byte for byte).
- `seed.py` — database rows built from the dataset (written to `seed/`, git-ignored).
- `review_sample.py` — builds `docs/PHASE1_SAMPLE.md`.

From the repo root:

    .venv/bin/python data/synthetic/generate.py     # regenerate orders/, events/ and manifest.json
    .venv/bin/python -m pytest -q
