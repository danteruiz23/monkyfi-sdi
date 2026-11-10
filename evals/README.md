# evals

One command, from the repo root:

    .venv/bin/python evals/run.py                      # denominators and scorer self-check
    .venv/bin/python evals/run.py --predictions DIR    # score an agent run
    .venv/bin/python evals/run.py --split dev          # dev | eval (default) | all

The agent writes `DIR/<order id>/v<N>/prediction.json` (`schemas/prediction.schema.json`); the runner compares it with the golden label and prints numerator, denominator, threshold and status for each eval in SPEC 12.1, plus the data present for the 16 mandatory cases. The 8 adversarial orders are always reported separately.

Before Phase 2 there is no agent output, so every eval is reported as NOT RUN with its denominator. The runner also checks its own scoring on every run: a perfect reference predictor must pass and a blind one must fail.

Results are written to `evals/results/latest.json` (git-ignored). Thresholds measured on synthetic data are a development signal, not production proof.
