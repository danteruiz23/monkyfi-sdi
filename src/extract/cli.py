"""Run extraction over the synthetic dataset. From the repo root:

    .venv/bin/python -m src.extract.cli --split eval --out runs/eval-latest
    .venv/bin/python evals/run.py --predictions runs/eval-latest

Model answers are recorded in runs/recordings/ (git-ignored). `--replay` re-runs from recordings
only, with no model call, so a result can be re-scored exactly. Credentials come from .env.

Writes <out>/<order>/v<N>/extraction.json and prediction.json, and <out>/run.json.
SYNTHETIC — NOT REAL DATA.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .. import ROOT
from ..ingest import read_package
from ..providers import ProviderError, RecordingProvider, ReplayProvider, load_dotenv, provider_from_env
from .extract import extract_version
from .prediction import check, to_prediction

DATA = ROOT / "data" / "synthetic"
RECORDINGS = ROOT / "runs" / "recordings"


def select_versions(data: Path, split: str, orders: list[str] | None) -> list[tuple[str, int, Path]]:
    """(order id, version, documents dir) from the manifest. Golden labels are never read here."""
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    chosen = []
    for order in manifest["orders"]:
        if orders and order["order_id"] not in orders:
            continue
        if not orders and split != "all" and order["split"] != split:
            continue
        for version in order["versions"]:
            chosen.append((order["order_id"], version, data / order["path"] / f"v{version}" / "documents"))
    return chosen


def make_provider(replay: bool, recordings: Path | None, provider_name: str | None = None):
    """Recordings live in one directory per provider and model (default runs/recordings/<provider>-<model>)."""
    if replay:
        if recordings is None:
            raise ProviderError("--replay needs --recordings DIR (one directory per provider and model)")
        meta_path = recordings / "recording.json"
        if not meta_path.exists():
            raise ProviderError(f"--replay: no recordings in {recordings}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return ReplayProvider(recordings, meta["provider"], meta["model"])
    inner = provider_from_env(provider_name)
    recordings = recordings or RECORDINGS / f"{inner.name}-{inner.model}"
    recordings.mkdir(parents=True, exist_ok=True)
    (recordings / "recording.json").write_text(json.dumps({"provider": inner.name, "model": inner.model}) + "\n",
                                               encoding="utf-8")
    return RecordingProvider(inner, recordings)


def add_usage(total: dict, calls: list[dict]) -> None:
    for call in calls:
        usage = call.get("usage") or {}
        total["calls"] += 1
        total["attempts"] += call.get("attempts", 1)
        total["cached_calls"] += bool(usage.get("cached"))
        for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
            total[name] += usage.get(name) or 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Critical-field extraction over the synthetic dataset")
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--split", choices=["dev", "eval", "adversarial", "all"], default="eval")
    parser.add_argument("--orders", nargs="*", help="only these order ids (overrides --split)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--provider", choices=["meta", "gemini"], help="overrides MODEL_PROVIDER")
    parser.add_argument("--recordings", type=Path,
                        help="where model answers are recorded (default runs/recordings/<provider>-<model>)")
    parser.add_argument("--replay", action="store_true", help="answer only from recordings; no model call")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    try:
        provider = make_provider(args.replay, args.recordings, args.provider)
    except ProviderError as exc:
        print(f"Not run: {exc}", file=sys.stderr)
        return 2

    versions = select_versions(args.data, args.split, args.orders)
    print("SYNTHETIC — NOT REAL DATA")
    print(f"Provider {provider.name} / {provider.model}{' (replay)' if args.replay else ''}; "
          f"{len(versions)} order versions → {args.out}")
    summary = {"synthetic": True, "provider": provider.name, "model": provider.model, "replay": args.replay,
               "split": args.split, "versions": [], "failures": [],
               "usage": {"calls": 0, "attempts": 0, "cached_calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
                         "total_tokens": 0}}
    for order_id, version_no, documents_dir in versions:
        try:
            documents = read_package(documents_dir)
            record = extract_version(documents, provider, order_dir_id=order_id, version_no=version_no)
            check("extraction.schema.json", record)
            prediction = to_prediction(record)
        except (ProviderError, ValueError, OSError) as exc:
            summary["failures"].append({"order": order_id, "version": version_no, "error": str(exc)})
            print(f"  {order_id} v{version_no}: FAILED — {exc}")
            continue
        add_usage(summary["usage"], record["model_calls"])
        target = args.out / order_id / f"v{version_no}"
        target.mkdir(parents=True, exist_ok=True)
        (target / "extraction.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                                                encoding="utf-8")
        (target / "prediction.json").write_text(json.dumps(prediction, indent=1, ensure_ascii=False) + "\n",
                                                encoding="utf-8")
        counts: dict[str, int] = {}
        for f in record["fields"]:
            counts[f["status"]] = counts.get(f["status"], 0) + 1
        summary["versions"].append({"order": order_id, "version": version_no, "product": record["product"],
                                    "statuses": counts, "rejected_mentions": len(record["rejected_mentions"])})
        print(f"  {order_id} v{version_no}: {record['product']} {counts} "
              f"rejected={len(record['rejected_mentions'])}")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "run.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(f"Done: {len(summary['versions'])} written, {len(summary['failures'])} failed. Usage: {summary['usage']}")
    return 1 if summary["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
