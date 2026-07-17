"""Blue/green interface reconciliation harness.

Proves incremental and full-refresh parity on identical final event sets:

- green: every batch loaded at once, all models built with --full-refresh;
- blue: the same batches loaded in chronological phases (base -> delta ->
  replay -> repair) with ordinary incremental runs, deliberately holding back
  one old-ingestion batch so the beyond-lookback miss is demonstrated in
  isolation before an explicit bounded backfill recovers it.

Comparison is exact: row counts, key sets and full row content at every
governed interface. No tolerance for keys or integer financial values. Emits a
machine-readable reconciliation artifact.

Usage: python -m tools.reconcile.compare_interfaces --scenario all
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]


def dbt_executable() -> str:
    found = shutil.which("dbt")
    if not found:
        raise RuntimeError("dbt executable not found on PATH (run via `uv run`)")
    return found

INTERFACES: dict[str, list[str]] = {
    "main_logical.lgl_growth_acquisition": ["application_id"],
    "main_logical.lgl_referral_economics": ["referral_id"],
    "main_logical.lgl_reward_entitlement": ["referral_id"],
    "main_logical.lgl_reward_ledger_reconciliation": ["referral_id", "reconciliation_date"],
    "main_logical.lgl_warehouse_health": ["model_name", "run_date"],
    "main_presentation.prs_financial_reconciliation_daily": ["reconciliation_date"],
}

MODEL_SELECTION = [
    "path:models/landing",
    "path:models/normalised",
    "path:models/logical",
    "path:models/presentation",
]


def run_dbt(
    db_path: Path,
    warehouse_dir: Path,
    *,
    full_refresh: bool = False,
    backfill: tuple[str, str] | None = None,
) -> None:
    dbt_vars = {"events_warehouse": warehouse_dir.as_posix()}
    if backfill:
        dbt_vars["backfill_start"], dbt_vars["backfill_end"] = backfill
    command = [
        dbt_executable(), "run",
        "--project-dir", "dbt_neobank", "--profiles-dir", "dbt_neobank",
        "--target", "dev", "--vars", json.dumps(dbt_vars),
        "--select", *MODEL_SELECTION,
    ]
    if full_refresh:
        command.append("--full-refresh")
    env = {**os.environ, "NEOBANK_DUCKDB_PATH": str(db_path)}
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"dbt run failed:\n{result.stdout[-4000:]}\n{result.stderr[-2000:]}")


def snapshot(db_path: Path) -> dict[str, dict]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        tables: dict[str, dict] = {}
        for table, keys in INTERFACES.items():
            order = ", ".join(keys)
            rows = con.sql(f"select * from {table} order by {order}").fetchall()
            canonical = json.dumps(rows, sort_keys=True, default=str)
            tables[table] = {
                "row_count": len(rows),
                "content_hash": hashlib.sha256(canonical.encode()).hexdigest(),
                "rows": rows,
            }
        return tables
    finally:
        con.close()


def compare_snapshots(green: dict, blue: dict) -> list[str]:
    differences: list[str] = []
    for table in INTERFACES:
        g, b = green[table], blue[table]
        if g["row_count"] != b["row_count"]:
            differences.append(
                f"{table}: row count green={g['row_count']} blue={b['row_count']}"
            )
        elif g["content_hash"] != b["content_hash"]:
            differences.append(f"{table}: content hash mismatch at identical row count")
    return differences


def make_phase_source(workdir: Path, name: str, batches: list[dict], source_dir: Path) -> Path:
    phase_dir = workdir / f"phase-{name}"
    (phase_dir / "batches").mkdir(parents=True, exist_ok=True)
    for batch in batches:
        shutil.copy2(source_dir / batch["path"], phase_dir / batch["path"])
    logical = hashlib.sha256("".join(b["checksum"] for b in batches).encode()).hexdigest()
    manifest = {
        "logical_checksum": logical,
        "batches": batches,
        "truth": {"delivery_count": sum(b["row_count"] for b in batches)},
    }
    (phase_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return phase_dir


def run_blue_green(source_dir: Path, workdir: Path) -> dict:
    from src.ingestion.event_loader import load_run
    from tools.reconcile.backfill import run_backfill

    source_dir, workdir = Path(source_dir), Path(workdir)
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    with open(source_dir / "manifest.json", encoding="utf-8") as f:
        batches = json.load(f)["batches"]
    batches.sort(key=lambda b: b["batch_id"])
    days = sorted({b["batch_id"].split("-", 1)[1][:10] for b in batches})
    if len(days) < 12:
        raise ValueError(f"need at least 12 ingestion days for phases, got {len(days)}")

    # Hold back one old-ingestion batch: a busy day from the middle of the base
    # range, so by the time it finally arrives every model's watermark is weeks
    # ahead and the 3-day lookback deliberately skips it on ordinary runs.
    cut = int(len(days) * 0.6)
    rows_by_day = {}
    for batch in batches:
        day = batch["batch_id"].split("-", 1)[1][:10]
        rows_by_day[day] = rows_by_day.get(day, 0) + batch["row_count"]
    candidate_days = days[5 : cut - 5]
    held_day = max(candidate_days, key=lambda day: (rows_by_day[day], day))
    base_days = set(days[:cut]) - {held_day}
    delta_days = set(days[cut:])

    def batches_for(day_set: set[str]) -> list[dict]:
        return [b for b in batches if b["batch_id"].split("-", 1)[1][:10] in day_set]

    held_batches = batches_for({held_day})

    # --- green: everything at once, full refresh -----------------------------
    green_db = workdir / "green.duckdb"
    green_warehouse = workdir / "green-warehouse"
    load_run(source_dir, green_warehouse)
    run_dbt(green_db, green_warehouse, full_refresh=True)
    green = snapshot(green_db)

    # --- blue: chronological incremental phases ------------------------------
    blue_db = workdir / "blue.duckdb"
    blue_warehouse = workdir / "blue-warehouse"

    base_source = make_phase_source(workdir, "base", batches_for(base_days), source_dir)
    load_run(base_source, blue_warehouse)
    run_dbt(blue_db, blue_warehouse)

    delta_source = make_phase_source(workdir, "delta", batches_for(delta_days), source_dir)
    load_run(delta_source, blue_warehouse)
    run_dbt(blue_db, blue_warehouse)
    after_delta = snapshot(blue_db)

    # Same-batch replay must be a no-op end to end.
    replay = load_run(delta_source, blue_warehouse)
    run_dbt(blue_db, blue_warehouse)
    after_replay = snapshot(blue_db)
    replay_differences = compare_snapshots(after_delta, after_replay)

    # Repair phase: the held-back old-ingestion batch arrives; the ordinary
    # lookback must miss it (demonstrated in isolation), then the explicit
    # bounded backfill recovers it.
    repair_source = make_phase_source(workdir, "repair", held_batches, source_dir)
    load_run(repair_source, blue_warehouse)
    run_dbt(blue_db, blue_warehouse)
    pre_backfill = compare_snapshots(green, snapshot(blue_db))

    backfill_start = held_day
    backfill_end_index = days.index(held_day) + 1
    backfill_end = days[backfill_end_index]
    run_backfill(
        db_path=blue_db,
        warehouse_dir=blue_warehouse,
        start=backfill_start,
        end=backfill_end,
        reason="blue/green repair phase: held-back batch beyond the 3-day lookback",
        operator="compare_interfaces-harness",
    )
    post_backfill = compare_snapshots(green, snapshot(blue_db))

    return {
        "source": str(source_dir),
        "interfaces": {t: green[t]["row_count"] for t in INTERFACES},
        "phases": {
            "base_days": len(base_days),
            "delta_days": len(delta_days),
            "held_back_day": held_day,
        },
        "replay_idempotent": replay_differences == [],
        "replay_skipped_batches": replay.batches_skipped,
        "pre_backfill_differences": pre_backfill,
        "pre_backfill_miss_demonstrated": len(pre_backfill) > 0,
        "backfill_window": [backfill_start, backfill_end],
        "post_backfill_differences": post_backfill,
        "parity": post_backfill == [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="all")
    parser.add_argument("--source", type=Path, default=ROOT / "data" / "generated" / "tiny-a")
    parser.add_argument("--workdir", type=Path, default=ROOT / "data" / "bluegreen")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts" / "plan2" / "blue-green-report.json"
    )
    args = parser.parse_args(argv)

    report = run_blue_green(args.source, args.workdir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report_for_disk = dict(report)
    args.output.write_text(
        json.dumps(report_for_disk, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    ok = report["parity"] and report["replay_idempotent"] and report[
        "pre_backfill_miss_demonstrated"
    ]
    print(
        f"parity={report['parity']} replay_idempotent={report['replay_idempotent']} "
        f"pre_backfill_miss={report['pre_backfill_miss_demonstrated']} "
        f"report={args.output}"
    )
    if not ok:
        for difference in report["pre_backfill_differences"]:
            print(f"pre-backfill: {difference}", file=sys.stderr)
        for difference in report["post_backfill_differences"]:
            print(f"post-backfill: {difference}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
