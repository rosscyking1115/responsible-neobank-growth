"""Append-only ingestion tests.

Frozen outcomes: replayed batches are idempotent at the batch registry; a
malformed payload lands in quarantine with evidence; a conflicting duplicate
(same idempotency key, different payload hash) is quarantined at high
severity; a corrupted batch fails alone without poisoning the run.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest

from src.event_simulator.config import load_config
from src.event_simulator.writers import write_output
from src.ingestion.event_loader import load_run

ROOT = Path(__file__).resolve().parents[2]
KNOWN_TRUTH_EVENTS = ROOT / "fixtures" / "events" / "tiny" / "referral-known-truth.jsonl"
CONFIG = load_config(ROOT / "config" / "simulator" / "tiny.yml")


def _known_truth_deliveries() -> list[dict]:
    with open(KNOWN_TRUTH_EVENTS, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_source(tmp_path: Path, deliveries: list[dict], name: str) -> Path:
    source = tmp_path / name
    faulted = SimpleNamespace(
        deliveries=sorted(deliveries, key=lambda e: (e["ingested_at"], e["event_id"])),
        manifest={"delivery_count": len(deliveries)},
    )
    write_output(faulted, CONFIG, source)
    return source


@pytest.fixture()
def loaded(tmp_path):
    source = _write_source(tmp_path, _known_truth_deliveries(), "source")
    warehouse = tmp_path / "warehouse"
    result = load_run(source, warehouse)
    return source, warehouse, result


def test_known_truth_fixture_loads_with_expected_quarantine(loaded) -> None:
    _, warehouse, result = loaded
    assert result.valid_rows == 20
    assert result.quarantined_rows == 1
    assert result.batches_loaded > 0 and result.batches_failed == 0

    raw_count = duckdb.sql(
        f"select count(*) from read_parquet('{warehouse.as_posix()}/raw_events/*.parquet')"
    ).fetchone()[0]
    assert raw_count == 20
    quarantine = duckdb.sql(
        "select error_code, retriable from "
        f"read_parquet('{warehouse.as_posix()}/quarantine/*.parquet')"
    ).fetchall()
    assert quarantine == [("schema_validation_failed", False)]


def test_replay_is_idempotent(loaded) -> None:
    source, warehouse, first = loaded
    replay = load_run(source, warehouse)
    assert replay.batches_loaded == 0
    assert replay.batches_skipped == first.batches_loaded
    assert replay.valid_rows == 0 and replay.quarantined_rows == 0
    raw_count = duckdb.sql(
        f"select count(*) from read_parquet('{warehouse.as_posix()}/raw_events/*.parquet')"
    ).fetchone()[0]
    assert raw_count == 20, "replaying a batch must not add rows"


def test_conflicting_duplicate_is_quarantined_high_severity(loaded, tmp_path) -> None:
    _, warehouse, _ = loaded
    original = next(
        e for e in _known_truth_deliveries() if e["event_name"] == "reward-booked"
    )
    conflict = {**original, "payload": dict(original["payload"])}
    conflict["event_id"] = "evt_conflicting-redelivery-01"
    conflict["payload"]["amount_minor"] = original["payload"]["amount_minor"] + 100
    conflict["ingested_at"] = "2026-01-09T09:00:00Z"

    source = _write_source(tmp_path, [conflict], "conflict-source")
    result = load_run(source, warehouse)
    assert result.valid_rows == 0
    assert result.quarantined_rows == 1
    rows = duckdb.sql(
        "select error_code, retriable from "
        f"read_parquet('{warehouse.as_posix()}/quarantine/*.parquet') "
        "where error_code = 'conflicting_duplicate'"
    ).fetchall()
    assert rows == [("conflicting_duplicate", False)]


def test_exact_redelivery_is_kept_as_delivery_evidence(loaded, tmp_path) -> None:
    """A same-payload redelivery is valid at the delivery layer; canonical
    dedup happens downstream in the landing/normalised models."""
    _, warehouse, _ = loaded
    original = next(
        e for e in _known_truth_deliveries() if e["event_name"] == "reward-booked"
    )
    redelivery = {**original, "payload": dict(original["payload"])}
    redelivery["event_id"] = "evt_exact-redelivery-000001"
    redelivery["ingested_at"] = "2026-01-09T10:00:00Z"

    source = _write_source(tmp_path, [redelivery], "redelivery-source")
    result = load_run(source, warehouse)
    assert result.valid_rows == 1 and result.quarantined_rows == 0


def test_corrupted_batch_fails_alone(loaded, tmp_path) -> None:
    _, warehouse, _ = loaded
    deliveries = [
        e for e in _known_truth_deliveries() if e["event_name"] == "campaign-spend-recorded"
    ]
    # Build a fresh two-day source, then corrupt one batch file after writing.
    extra = _known_truth_deliveries()[:4]
    source = _write_source(tmp_path, extra, "corrupt-source")
    batch_files = sorted((source / "batches").glob("*.jsonl"))
    assert len(batch_files) >= 2, f"need multiple batches, got {len(batch_files)}"
    batch_files[0].write_text(
        batch_files[0].read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )

    result = load_run(source, warehouse)
    assert result.batches_failed == 1, "checksum mismatch must fail exactly that batch"
    assert result.batches_loaded == len(batch_files) - 1
    del deliveries


def test_run_manifest_records_every_run(loaded) -> None:
    source, warehouse, first = loaded
    load_run(source, warehouse)  # replay
    runs_file = warehouse / "registry" / "runs.jsonl"
    runs = [json.loads(line) for line in runs_file.read_text(encoding="utf-8").splitlines()]
    assert len(runs) == 2
    assert runs[0]["valid_rows"] == first.valid_rows
    assert runs[1]["batches_skipped"] == first.batches_loaded
    for run in runs:
        assert run["run_id"] and run["source"]
