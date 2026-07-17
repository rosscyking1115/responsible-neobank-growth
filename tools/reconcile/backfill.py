"""Explicit bounded backfill (docs/contracts/incremental-correctness.md).

Re-runs the incremental event models with a bounded ingestion window
(``backfill_start`` inclusive, ``backfill_end`` exclusive) so arrivals older
than the ordinary lookback are recovered. Reason and operator are mandatory
and recorded in an append-only log; an unbounded full refresh is a separate
recovery path and is never triggered from here.

Usage:
    python -m tools.reconcile.backfill --start 2026-02-20 --end 2026-02-21 \
        --reason "late partition redelivery" --operator ross \
        [--db neobank.duckdb] [--warehouse data/warehouse]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "artifacts" / "plan2" / "backfill-log.jsonl"

MODEL_SELECTION = [
    "path:models/normalised",
    "path:models/logical",
    "path:models/presentation",
]


def run_backfill(
    *,
    db_path: Path,
    warehouse_dir: Path,
    start: str,
    end: str,
    reason: str,
    operator: str,
) -> None:
    if not reason.strip() or not operator.strip():
        raise ValueError("backfill requires a non-empty reason and operator")
    if not start < end:
        raise ValueError("backfill window must be a non-empty range (start < end)")

    dbt_vars = {
        "events_warehouse": Path(warehouse_dir).as_posix(),
        "backfill_start": start,
        "backfill_end": end,
    }
    dbt = shutil.which("dbt")
    if not dbt:
        raise RuntimeError("dbt executable not found on PATH (run via `uv run`)")
    command = [
        dbt, "run",
        "--project-dir", "dbt_neobank", "--profiles-dir", "dbt_neobank",
        "--target", "dev", "--vars", json.dumps(dbt_vars),
        "--select", *MODEL_SELECTION,
    ]
    env = {**os.environ, "NEOBANK_DUCKDB_PATH": str(db_path)}
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"backfill dbt run failed:\n{result.stdout[-4000:]}\n{result.stderr[-2000:]}"
        )

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8", newline="\n") as f:
        f.write(
            json.dumps(
                {
                    "executed_at": datetime.now(UTC).isoformat(),
                    "backfill_start": start,
                    "backfill_end": end,
                    "reason": reason,
                    "operator": operator,
                    "database": str(db_path),
                    "warehouse": str(warehouse_dir),
                },
                sort_keys=True,
            )
            + "\n"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--db", type=Path, default=ROOT / "neobank.duckdb")
    parser.add_argument("--warehouse", type=Path, default=ROOT / "data" / "warehouse")
    args = parser.parse_args(argv)
    run_backfill(
        db_path=args.db,
        warehouse_dir=args.warehouse,
        start=args.start,
        end=args.end,
        reason=args.reason,
        operator=args.operator,
    )
    print(f"backfill complete: [{args.start}, {args.end}) recorded in {LOG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
