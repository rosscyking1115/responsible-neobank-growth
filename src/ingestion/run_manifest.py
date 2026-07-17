"""Batch registry and run manifests for ingestion (Plan 2 section 6.1).

The registry is the idempotency boundary: a batch (content-scoped id plus
checksum) loads exactly once. The keymap carries accepted
idempotency-key/payload-hash pairs across runs so conflicting duplicates are
detectable. Run manifests are append-only operational evidence.
"""

import json
from pathlib import Path


def _registry_dir(warehouse_dir: Path) -> Path:
    path = Path(warehouse_dir) / "registry"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _append_jsonl(path: Path, record: dict) -> None:
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def registered_batches(warehouse_dir: Path) -> dict[str, str]:
    """batch_id -> checksum for every batch already loaded."""
    records = _read_jsonl(_registry_dir(warehouse_dir) / "batches.jsonl")
    return {record["batch_id"]: record["checksum"] for record in records}


def register_batch(warehouse_dir: Path, batch: dict, valid: int, quarantined: int) -> None:
    _append_jsonl(
        _registry_dir(warehouse_dir) / "batches.jsonl",
        {
            "batch_id": batch["batch_id"],
            "checksum": batch["checksum"],
            "row_count": batch["row_count"],
            "valid_rows": valid,
            "quarantined_rows": quarantined,
        },
    )


def load_keymap(warehouse_dir: Path) -> dict[str, str]:
    """idempotency_key -> payload_hash for all previously accepted deliveries."""
    records = _read_jsonl(_registry_dir(warehouse_dir) / "keymap.jsonl")
    return {record["idempotency_key"]: record["payload_hash"] for record in records}


def append_keymap(warehouse_dir: Path, entries: dict[str, str]) -> None:
    path = _registry_dir(warehouse_dir) / "keymap.jsonl"
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        for key, digest in sorted(entries.items()):
            f.write(
                json.dumps({"idempotency_key": key, "payload_hash": digest}, sort_keys=True)
                + "\n"
            )


def append_run(warehouse_dir: Path, record: dict) -> None:
    _append_jsonl(_registry_dir(warehouse_dir) / "runs.jsonl", record)
