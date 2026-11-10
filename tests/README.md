# tests

Python tests. From the repo root: `.venv/bin/python -m pytest -q`

- `test_dataset.py` — rules files, dataset composition, and every order version: schema, synthetic mark on every PDF page, complete package, sources on the cited page, findings, the G1 rule (D28), dates, determinism.
- `test_schemas.py` — entity schemas against the SQL migration, RLS policies, and the rows built from the dataset.
- `test_evals_and_locales.py` — the eval runner's scoring and the locale files.
