# evals

One command, from the repo root:

    .venv/bin/python evals/run.py                      # denominators and scorer self-check
    .venv/bin/python evals/run.py --predictions DIR    # score an agent run
    .venv/bin/python evals/run.py --split dev          # dev | eval (default) | all

The agent writes `DIR/<order id>/v<N>/prediction.json` (`schemas/prediction.schema.json`); the runner compares it with the golden label and prints numerator, denominator, threshold and status for each eval in SPEC 12.1, plus the data present for the 16 mandatory cases. The 8 adversarial orders are always reported separately.

`src/extract/cli.py` writes the predictions' fields (Phase 2) and `src/validators/cli.py` adds findings, gate and reopened validations (Phase 3); see `src/README.md`. The agent names a source by its file name and the runner maps file names to the labels' document ids. An eval with no prediction section is reported as NOT RUN with its denominator. The runner also checks its own scoring on every run: a perfect reference predictor must pass and a blind one must fail.

Results are written to `evals/results/latest.json` (git-ignored). Thresholds measured on synthetic data are a development signal, not production proof.

## Phase 4: dates

Run the planner first (`python -m src.planner.cli --run <run>`), which adds `dates` to each `prediction.json`. Three date results: **Dates** (recall of labeled mentions with the right type and scope, 100%), **Dates: no forecast or informal date as committed** (order dates typed committed that the labels do not type committed, must be 0) and **Dates: unlabeled or mistyped mentions** (reported).

**Dependencies** (Phase 4, cases 5 and 6): each labeled supplier dependency must be predicted with the same supplier, date, date type, order forecast status and follow-up flag (100%). The planner writes `dependencies` to `prediction.json`.

**Shared resources** (Phase 4, case 7): per order, the predicted shared resources must equal the labels (id, kind, blocked, linked orders); an order with none labeled must get none. The planner links orders across the run folder, so plan the whole folder at once.
