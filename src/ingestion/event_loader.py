"""Append-only local event loader.

Reads a generated run (batches + manifest), verifies each batch's checksum,
classifies deliveries against the registry and keymap, and appends immutable
per-batch Parquet files: valid deliveries to ``raw_events/`` and quarantined
ones to ``quarantine/``. Replaying a batch is a no-op at the batch registry; a
corrupted batch fails alone without poisoning the run.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from src.event_simulator.registry import EventRegistry
from src.ingestion import run_manifest as registry_store
from src.ingestion.quarantine import classify, payload_hash


@dataclass
class LoadResult:
    run_id: str
    batches_loaded: int
    batches_skipped: int
    batches_failed: int
    valid_rows: int
    quarantined_rows: int


def _raw_row(event: dict, batch_id: str, run_id: str) -> dict:
    return {
        "event_id": event["event_id"],
        "idempotency_key": event["idempotency_key"],
        "event_name": event["event_name"],
        "source_service": event["source_service"],
        "occurred_at": event["occurred_at"],
        "emitted_at": event["emitted_at"],
        "ingested_at": event["ingested_at"],
        "schema_version": event["schema_version"],
        "producer_id": event["producer_id"],
        "trace_id": event["trace_id"],
        "payload": json.dumps(event["payload"], sort_keys=True),
        "payload_hash": payload_hash(event["payload"]),
        "generator_version": event["generator_version"],
        "scenario_id": event["scenario_id"],
        "batch_id": batch_id,
        "run_id": run_id,
        "arrival_date": event["ingested_at"][:10],
    }


def _quarantine_row(event: dict, classification, batch_id: str, run_id: str) -> dict:
    return {
        "event_id": event.get("event_id"),
        "event_name": event.get("event_name"),
        "source_service": event.get("source_service"),
        "ingested_at": event.get("ingested_at"),
        "schema_version": event.get("schema_version"),
        "payload_raw": json.dumps(event.get("payload"), sort_keys=True),
        "payload_hash": payload_hash(event.get("payload") or {}),
        "error_code": classification.error_code,
        "error_message": classification.error_message,
        "retriable": classification.retriable,
        "severity": classification.severity,
        "scenario_id": event.get("scenario_id"),
        "batch_id": batch_id,
        "run_id": run_id,
        "arrival_date": (event.get("ingested_at") or "")[:10],
    }


def load_run(source_dir: Path, warehouse_dir: Path) -> LoadResult:
    source_dir, warehouse_dir = Path(source_dir), Path(warehouse_dir)
    with open(source_dir / "manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)
    run_id = f"run-{manifest['logical_checksum'][:16]}"

    registry = EventRegistry.load()
    known_batches = registry_store.registered_batches(warehouse_dir)
    keymap = registry_store.load_keymap(warehouse_dir)

    (warehouse_dir / "raw_events").mkdir(parents=True, exist_ok=True)
    (warehouse_dir / "quarantine").mkdir(parents=True, exist_ok=True)

    loaded = skipped = failed = valid_total = quarantined_total = 0

    for batch in manifest["batches"]:
        if known_batches.get(batch["batch_id"]) == batch["checksum"]:
            skipped += 1
            continue

        content = (source_dir / batch["path"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != batch["checksum"]:
            failed += 1
            continue

        events = [json.loads(line) for line in content.decode("utf-8").splitlines() if line]
        events.sort(key=lambda e: (e.get("ingested_at", ""), e.get("event_id", "")))

        raw_rows: list[dict] = []
        quarantine_rows: list[dict] = []
        new_keys: dict[str, str] = {}
        for event in events:
            classification = classify(event, registry, keymap)
            if classification.status == "valid":
                row = _raw_row(event, batch["batch_id"], run_id)
                raw_rows.append(row)
                keymap[event["idempotency_key"]] = row["payload_hash"]
                new_keys[event["idempotency_key"]] = row["payload_hash"]
            else:
                quarantine_rows.append(
                    _quarantine_row(event, classification, batch["batch_id"], run_id)
                )

        if raw_rows:
            pl.DataFrame(raw_rows).write_parquet(
                warehouse_dir / "raw_events" / f"{batch['batch_id']}.parquet"
            )
        if quarantine_rows:
            pl.DataFrame(quarantine_rows).write_parquet(
                warehouse_dir / "quarantine" / f"{batch['batch_id']}.parquet"
            )

        registry_store.register_batch(
            warehouse_dir, batch, valid=len(raw_rows), quarantined=len(quarantine_rows)
        )
        if new_keys:
            registry_store.append_keymap(warehouse_dir, new_keys)
        loaded += 1
        valid_total += len(raw_rows)
        quarantined_total += len(quarantine_rows)

    result = LoadResult(
        run_id=run_id,
        batches_loaded=loaded,
        batches_skipped=skipped,
        batches_failed=failed,
        valid_rows=valid_total,
        quarantined_rows=quarantined_total,
    )
    registry_store.append_run(
        warehouse_dir,
        {
            "run_id": run_id,
            "source": str(source_dir),
            "batches_loaded": loaded,
            "batches_skipped": skipped,
            "batches_failed": failed,
            "valid_rows": valid_total,
            "quarantined_rows": quarantined_total,
        },
    )
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--warehouse", required=True, type=Path)
    args = parser.parse_args(argv)
    result = load_run(args.source, args.warehouse)
    print(
        f"{result.run_id}: loaded={result.batches_loaded} skipped={result.batches_skipped} "
        f"failed={result.batches_failed} valid={result.valid_rows} "
        f"quarantined={result.quarantined_rows}"
    )
    return 1 if result.batches_failed else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
