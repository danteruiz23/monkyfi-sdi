# src

Python package: ingestion, extraction, validators, planner, comms, acceptance, audit and the model provider layer. Run modules from the repo root (`.venv/bin/python -m src.<module>`).

Built so far (Phase 2):

- `ingest/` — reads PDF (pypdf) and DOCX (no extra dependency) page by page, with file hash, document type from the title (`rules/extraction.json`) and ingestion time. No OCR.
- `providers/` — one interface for every model call. `meta` is Muse Spark 1.1 via Meta Model API (OpenAI-compatible). Answers are validated against a JSON Schema with bounded retries, recorded in `runs/recordings/` and can be replayed offline. `fake.py` is for tests only. Gemini is not built (D23 open).
- `extract/` — critical-field extraction. The model proposes mentions per document; deterministic code grounds them (the text must be printed on the cited page), normalizes them and sets the status of each field across documents.

Run:

    .venv/bin/python -m src.extract.cli --split eval --out runs/eval-latest   # needs .env
    .venv/bin/python -m src.extract.cli --split eval --out runs/eval-latest --replay
    .venv/bin/python evals/run.py --predictions runs/eval-latest

Empty until their phase: `validators/`, `planner/`, `comms/`, `acceptance/`, `audit/`. See `docs/SPEC.md`.
