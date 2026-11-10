# data/synthetic

Synthetic orders, documents and golden labels. Everything here is **SYNTHETIC — NOT REAL DATA**: companies, people, addresses and identifiers are fictional, and no real company names are used.

- `generate.py` — the generator. Builds each order from a "truth" plus seeded defects, so the golden label is known by construction.
- `example_orders.py` — the two example orders (one EPL, one wavelength) for Dante's review (D24).
- `examples/<order id>/documents/` — the order package: quote, signed order form, technical annex, LOA-CFA, emails.
- `examples/<order id>/golden.json` — expected fields, findings, G1 recommendation and date types.

Regenerate and check, from the repo root:

    .venv/bin/python data/synthetic/generate.py
    .venv/bin/python -m pytest -q

Documents are Markdown for now so they can be reviewed quickly. PDF rendering of the signed order form is added with the full dataset (Proposed).
