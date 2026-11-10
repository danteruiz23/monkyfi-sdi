# HANDOFF

## 0. Header

- **Project:** Monkyfi Service Delivery Intelligence
- **Session:** Phase 2 — ingestion and extraction (UC02 partial, RF01)
- **Date:** 2026-11-10
- **Status:** Done. Dante accepted the results; exit criteria met (D37).
- **Not done on purpose:** nothing from Phase 3 was started. The database migration is still not applied anywhere.

## a) Summary of tasks

- [x] Phase 1 committed at the start of the session (`784340f`).
- [x] PDF reading (pypdf) and DOCX reading (no extra dependency), page by page, with SHA-256, document type from the title and ingestion time. No OCR.
- [x] Provider layer: Muse Spark 1.1 (Meta Model API) and gemini-3.8-flash, both through OpenAI-compatible clients. Answers validated against a JSON Schema with bounded retries; every answer recorded and replayable offline.
- [x] Extraction: the model proposes mentions per document; deterministic code keeps only text printed on the cited page, normalizes by value type and sets each field's status across documents.
- [x] Statuses: extraction sets pending, missing, not_applicable, contradictory; `verified` needs a named human; `stale` marks a value superseded by a newer version (`src/extract/status.py`).
- [x] `prediction.json` and `extraction.json` per order version; the eval runner maps source file names to document ids.
- [x] Decisions D34–D40 recorded in `docs/DECISIONS.md` and `docs/SPEC.md` (v1.3). SYN-WAV-0019 relabeled (D35).
- [x] Eval split run and scored on both models with the same prompt and rules.

**Tests:** `.venv/bin/python -m pytest -q` → 817 passed.

**Evals:** `.venv/bin/python evals/run.py --predictions runs/eval-meta` → extraction and traceability PASS; all other evals NOT RUN (their phases come later). Scorer self-check OK. Same result for `runs/eval-gemini`.

Eval split, synthetic (12 orders, 13 order versions, 71 documents):

| | Muse Spark 1.1 (primary) | gemini-3.8-flash (comparison) |
|---|---|---|
| Critical field extraction | 828/828, 100% PASS | 828/828, 100% PASS |
| EPL / Wavelength | 366/366 / 462/462 | 366/366 / 462/462 |
| Factual traceability | 761/761, 100% | 761/761, 100% |
| Fields below 95% | none | none |
| Rejected values (not on the cited page) | 0 | 0 |
| Schema retries | 0 | 0 |
| Model calls | 71 | 71 |
| Prompt / completion / total tokens | 201,700 / 330,356 / 532,056 | 218,039 / 61,792 / 567,129 |
| Reasoning tokens | 275,920 (83.5% of output) | not reported separately |
| Time per call, mean / median / max | 10.1 s / 9.6 s / 26.5 s | 42.2 s / 26.8 s / 212.5 s |
| Model time per order (orders with no replayed calls) | 43–76 s, 11 orders | 150–345 s, 12 orders |

The PRD's 98% target, reported for information only (D34), is met by both. Gemini's total exceeds prompt + completion by 287,298 tokens, probably thinking tokens (inferred, not reported by the API). Token counts include the few calls answered from recordings (Muse Spark 6, Gemini 1). Thresholds on synthetic data are a development signal, not production proof: the PDFs are clean and text-based, so this run does not tell the models apart (D39).

## b) Next steps for the next session

1. Phase 3 (SPEC section 14): EPL and wavelength checklists, comparison across documents and versions, severity, findings with owner, due date and action, the G1 recommendation, and override with reason and approver. Build on `extraction.json`: contradictory and missing fields are already there with all their sources.
2. Phase 3 exit: critical recall ≥95%, precision ≥90%, zero not-ready orders passed, zero findings on clean orders, only affected validations reopened on v2; mandatory cases 1, 2, 3, 4 and 8.
3. Keep the backlog in view: D38 (Phase 7, log API retries with reason), D39 (hard synthetic subset before the demo), D40 (lower reasoning effort on Muse Spark, keep ≥95%).

**Prompt to start the next session** (open it at the repo root, not in `docs/`):

> /prime phase 3

## c) Friction points

- **Silent client retries.** The OpenAI client retries 429 and timeouts up to 2 times without logging, so slow Gemini calls (up to 212 s) cannot be attributed to rate limiting or to long answers. Handled: no failures, and the latency includes the retries. Unresolved: backlog D38 for Phase 7.
- **Output buffering.** The CLI's per-order lines did not appear in the log until the run ended (stdout written to a file). Progress had to be read from recordings. Unresolved; running with `python -u` would fix it.
- **Clean data.** 100% on both models says the pipeline works, not which model is better. Unresolved: D39.
- **Session working directory is `docs/`.** Every shell command needs `cd /Users/danteruiz7/monkyfi-sdi` first. Unresolved.
- **No local Postgres.** Extraction writes JSON records shaped like `field_value` rows; nothing is written to a database. Unresolved, unchanged since Phase 1.

## d) Changes in the plan

Recorded in `docs/SPEC.md` (v1.3) and `docs/DECISIONS.md`:

- D34: Phase 2 passes at ≥95%; the PRD's 98% is information only. The eval runner now scores extraction at ≥95% and notes the 98%.
- D35: emails never set or contradict contractual field values; in Phase 4 they are evidence for tentative dates (forecast only). SYN-WAV-0019's other-customer email is now a Phase 7 segregation finding (`SEG-OTHER-CUSTOMER`), not a field contradiction. The generator allows a `SEG-*` finding without a defective field.
- D36: Gemini (gemini-3.8-flash) kept as the comparison model; resolves D23.
- D37: Phase 2 Done; Muse Spark primary, Gemini comparison.
- D38–D40: backlog (retry logging, hard subset, reasoning effort).

**Choices made in this session that are not decisions (Proposed):**

- `rules/extraction.json`: document type from the title; only quote, order form, technical annex and LOA-CFA can set field values; placeholder texts for not applicable ("Not applicable", "N/A") and awaited ("To be confirmed", "TBC").
- A conditional field with nothing printed and a condition that cannot be evaluated is `missing` (the conservative reading).
- Field-level `stale` follows the labels: a value from a document not reissued for the current version stays `pending`, with the source marked as from an earlier version.
- The model sees the catalog of both products; the product's own field list is applied after the product is read from the documents.
- Gemini is called through Google's OpenAI-compatible endpoint, so both models receive identical requests.

**Open questions (SPEC section 17):** G1 and non-critical gaps; demo order with 3 defects; migration not applied; web framework and i18n library; commercial model.

## e) File paths

Commits on `main` this session: `784340f` (Phase 1), `03ac08f` (Phase 2 pipeline, D34–D36), and the hand-off commit with D37–D40.

**Entry points**

- `src/extract/cli.py` — created. Runs extraction over a split (`--provider`, `--orders`, `--replay`); writes `extraction.json`, `prediction.json` and `run.json` with token totals.
- `evals/run.py` — modified. Maps source file names to document ids; extraction threshold ≥95% with the PRD 98% as a note (D34).

**Modules**

- `src/__init__.py` — created. Repo paths for rules, prompts and schemas.
- `src/ingest/__init__.py` — created. Package exports.
- `src/ingest/documents.py` — created. `Document`/`Page`, title-based type, hash, package reading, whitespace squashing.
- `src/ingest/pdf.py` — created. PDF text per page with pypdf; refuses encrypted PDFs.
- `src/ingest/docx.py` — created. DOCX text from `word/document.xml` (paragraphs, table cells; tracked deletions skipped).
- `src/providers/__init__.py` — created. Provider selection (`meta`, `gemini`) and `.env` loading without printing values.
- `src/providers/base.py` — created. Provider interface, JSON parsing, schema validation with bounded retries.
- `src/providers/openai_compatible.py` — created. OpenAI-compatible client for Muse Spark and Gemini; JSON Schema response format with fallback to JSON mode.
- `src/providers/cache.py` — created. Recording and replay of model answers.
- `src/providers/fake.py` — created. Scripted provider for tests only.
- `src/extract/__init__.py` — created. Division of labor between model and code.
- `src/extract/catalog.py` — created. Field catalog from `rules/`, endpoint expansion, prompt descriptions, rules version.
- `src/extract/normalize.py` — created. Normalization by value type, placeholder detection; never guesses.
- `src/extract/ground.py` — created. Keeps a mention only if its text is on the cited page; corrects the page or rejects.
- `src/extract/consolidate.py` — created. Field status across documents; authoritative source; conditional fields.
- `src/extract/extract.py` — created. Prompt building, one call per document, extraction record.
- `src/extract/prediction.py` — created. Projection to `prediction.json`; schema checks.
- `src/extract/status.py` — created. The six statuses; `mark_verified` (named human) and `mark_stale`.
- `src/ingest/.gitkeep`, `src/providers/.gitkeep` — deleted. Folders now have code.

**Prompts and rules**

- `prompts/system.md` — created. Stable system prompt (`system@0.1.0`).
- `prompts/extract_fields.md` — created. Extraction task prompt (`extract_fields@0.1.0`).
- `rules/extraction.json` — created. Document types, field-source document types, placeholders (Proposed).

**Configuration and environment**

- `requirements-dev.txt` — modified. Adds `openai`.
- `.gitignore` — modified. Ignores `runs/` (run outputs and recorded model answers).
- `.env.example` — modified. Gemini comment updated; variable names unchanged: `MODEL_PROVIDER`, `META_MODEL_API_KEY`, `META_MODEL_API_BASE_URL`, `META_MODEL_NAME`, `GEMINI_API_KEY`, `GEMINI_MODEL_NAME`.

**Schemas and data**

- `schemas/extraction.schema.json` — created. Shape of `extraction.json`; no value without a source.
- `data/synthetic/dataset.py` — modified. SYN-WAV-0019 email no longer a `customer_name` source (D35).
- `data/synthetic/generate.py` — modified. Allows a `SEG-*` finding without a defective field.
- `data/synthetic/orders/SYN-WAV-0019/v1/golden.json` — regenerated. `customer_name` pending; finding `SEG-OTHER-CUSTOMER` kept; G1 still block. No PDF changed.

**Tests**

- `tests/test_extraction.py` — created. Reading, classification, DOCX, normalization against every golden value, grounding, statuses, full pipeline on all 48 versions with a golden-scripted model, invented values on clean orders, prompt framing, providers, recording/replay, CLI, eval mapping.
- `tests/test_dataset.py` — modified. Segregation findings may stand without a defective field (D35).
- `tests/conftest.py` — modified. Adds the repo root to the import path.

**Documentation**

- `docs/SPEC.md` — modified. v1.3: Phase 2 Done with results, Phase 7 retry logging, second model decided, D34 note in 12.1, backlog and open items in 17.
- `docs/DECISIONS.md` — modified. D34–D40.
- `docs/HANDOFF.md` — rewritten. This file.
- `src/README.md`, `prompts/README.md`, `rules/README.md`, `evals/README.md` — modified. Describe the Phase 2 code and commands.

**Not in the repo (git-ignored)**

- `runs/eval-meta/`, `runs/eval-gemini/` — predictions, extraction records, `run.json` and `eval_results.json` for both models.
- `runs/recordings/meta-muse-spark-1.1/`, `runs/recordings/gemini-gemini-3.8-flash/` — recorded model answers for offline replay.

**Commands** (from the repo root)

- Setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`
- Tests: `.venv/bin/python -m pytest -q`
- Extraction (needs `.env`): `.venv/bin/python -m src.extract.cli --provider meta --split eval --out runs/eval-meta`
- Replay without model calls: `.venv/bin/python -m src.extract.cli --replay --recordings runs/recordings/meta-muse-spark-1.1 --split eval --out runs/eval-meta`
- Evals: `.venv/bin/python evals/run.py --predictions runs/eval-meta`
- Regenerate the dataset: `.venv/bin/python data/synthetic/generate.py`
- App: none yet.

## History

- Phase 0 · 2026-11-09 · Done — deliverables committed, SPEC approved (D18), amendments D19–D23 applied.
- Phase 1 · 2026-11-09 · Done — 44 orders as PDF with golden labels, 18 entity schemas, RLS migration (not executed), eval runner, locales; sample approved (D33).
- Phase 2 · 2026-11-10 · Done — PDF/DOCX ingestion, provider layer (Muse Spark, Gemini), grounded extraction; 828/828 on the eval split on both models (D37).
