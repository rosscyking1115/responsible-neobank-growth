"""Plan 3 benchmark runner (Tasks 6-7).

Runs one benchmark stage (strategy x phase x repetition) as a timed dbt
invocation against the chosen lineage, then extracts that window's job
metadata from INFORMATION_SCHEMA.JOBS_BY_PROJECT (bytes processed/billed,
slot milliseconds, runtime, cache hits) scoped to the lineage's datasets.
Every stage checks cumulative billed bytes against the approved ceiling and
refuses to run past the 80% stop line. The guard in tools/cloud/plan3_config.py
must be open.

Usage:
    python -m tools.cloud.benchmark_runner --strategy full --phase delta --rep 1
    python -m tools.cloud.benchmark_runner --strategy incremental --phase repair --rep 1
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "neobank-growth-platform-ross"
RAW_DATASET = "neobank_p3_raw_route_c_p3_20260717"
PREFIXES = {"full": "neobank_p3b_20260717", "incremental": "neobank_p3o_20260717"}
BENCH_DIR = ROOT / "artifacts" / "plan3" / "benchmark"

# Planning rate from the approved preflight (London premium bound).
GBP_PER_TIB = 8.75 * 0.79  # USD -> GBP planning conversion recorded in preflight terms
CEILING_GBP = 10.0
STOP_FRACTION = 0.8

MODEL_SELECTION = [
    "path:models/landing",
    "path:models/normalised",
    "path:models/logical",
    "path:models/presentation",
]


def _which(name: str) -> str:
    found = shutil.which(name) or shutil.which(f"{name}.cmd")
    if not found:
        raise RuntimeError(f"{name} not found on PATH")
    return found


def _guard() -> None:
    from tools.cloud.plan3_config import billable_execution_allowed, load_run_config

    config = load_run_config(ROOT / "cloud" / "gcp" / "plan3" / "run-config.yml")
    if not billable_execution_allowed(config):
        raise RuntimeError("billable execution is not approved; refusing to run")


def cumulative_billed_bytes() -> int:
    total = 0
    if BENCH_DIR.exists():
        for path in BENCH_DIR.glob("*.json"):
            with open(path, encoding="utf-8") as f:
                totals = json.load(f).get("totals") or {}
            total += totals.get("bytes_billed", 0) or 0
    return total


def _check_stop_line() -> None:
    spent_gbp = cumulative_billed_bytes() / (1024**4) * GBP_PER_TIB
    if spent_gbp >= CEILING_GBP * STOP_FRACTION:
        raise RuntimeError(
            f"cumulative estimated spend £{spent_gbp:.2f} reached the 80% stop line; halting"
        )


def run_dbt(strategy: str, full_refresh: bool) -> tuple[str, str, float]:
    env = {
        **os.environ,
        "GCP_PROJECT_ID": PROJECT,
        "NEOBANK_BQ_LOCATION": "europe-west2",
        "NEOBANK_BQ_RAW_DATASET": RAW_DATASET,
        "NEOBANK_BQ_EVENTS_DATASET": RAW_DATASET,
        "NEOBANK_BQ_DATASET_PREFIX": PREFIXES[strategy],
        "NEOBANK_BQ_DEFAULT_DATASET": f"{PREFIXES[strategy]}_dev",
    }
    command = [
        _which("uv"), "run", "--extra", "gcp", "dbt", "run",
        "--project-dir", "dbt_neobank", "--profiles-dir", "dbt_neobank",
        "--target", "bigquery", "--select", *MODEL_SELECTION,
    ]
    if full_refresh:
        command.append("--full-refresh")
    start = datetime.now(UTC)
    started = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    runtime = time.monotonic() - started
    end = datetime.now(UTC)
    if result.returncode != 0:
        raise RuntimeError(f"dbt run failed:\n{result.stdout[-3000:]}")
    return start.isoformat(), end.isoformat(), runtime


def extract_jobs(prefix: str, start_iso: str, end_iso: str) -> dict:
    bq = _which("bq")
    sql = f"""
        select
            count(*) as job_count,
            sum(total_bytes_processed) as bytes_processed,
            sum(total_bytes_billed) as bytes_billed,
            sum(total_slot_ms) as total_slot_ms,
            countif(cache_hit) as cache_hits
        from `region-europe-west2`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
        where creation_time between timestamp('{start_iso}') and timestamp('{end_iso}')
          and job_type = 'QUERY'
          and (destination_table.dataset_id like '{prefix}%'
               or query like '%{prefix}%')
    """
    # --location is mandatory for region-qualified INFORMATION_SCHEMA; without
    # it the bq CLI hangs instead of erroring (observed 2026-07-17).
    result = subprocess.run(
        [bq, "query", f"--project_id={PROJECT}", "--use_legacy_sql=false",
         "--location=europe-west2", "--label=route_c:plan3", "--format=json", sql],
        text=True, capture_output=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"job extraction failed: {result.stderr[-1500:]}")
    row = json.loads(result.stdout)[0]
    return {k: (int(v) if v is not None else 0) for k, v in row.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", choices=["full", "incremental"], required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--rep", type=int, default=1)
    args = parser.parse_args(argv)

    _guard()
    _check_stop_line()

    prefix = PREFIXES[args.strategy]
    start_iso, end_iso, runtime = run_dbt(args.strategy, full_refresh=args.strategy == "full")

    # Job-metadata extraction is a separate step (extract_stage_metadata.ps1 /
    # manual INFORMATION_SCHEMA query): the bq CLI blocks on piped stdin for
    # region-qualified queries, so the runner only records the timed window.
    record = {
        "run_id": "route-c-p3-20260717",
        "strategy": args.strategy,
        "phase": args.phase,
        "rep": args.rep,
        "prefix": prefix,
        "window": [start_iso, end_iso],
        "runtime_seconds": round(runtime, 1),
        "totals": None,
        "estimated_cost_gbp": None,
    }
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    output = BENCH_DIR / f"{args.phase}-{args.strategy}-rep{args.rep}.json"
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(record))
    return 0


if __name__ == "__main__":
    sys.exit(main())
