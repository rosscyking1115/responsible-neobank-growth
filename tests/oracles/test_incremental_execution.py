"""Incremental execution proof (Plan 2, Task 9).

Runs the blue/green harness end to end on the tiny profile: chronological
batches, same-batch replay, beyond-lookback hold-back with demonstrated miss,
explicit bounded backfill, and exact full-refresh parity at every governed
interface. Requires the generated tiny output; skips with instructions
otherwise.
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "data" / "generated" / "tiny-a"

pytestmark = pytest.mark.skipif(
    not (GENERATED / "manifest.json").exists(),
    reason=(
        "requires the generated tiny profile: uv run python -m src.event_simulator.cli "
        "generate --profile tiny --output data/generated/tiny-a"
    ),
)


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    from tools.reconcile.compare_interfaces import run_blue_green

    workdir = tmp_path_factory.mktemp("bluegreen")
    return run_blue_green(GENERATED, workdir)


def test_full_refresh_and_incremental_reach_exact_parity(report) -> None:
    assert report["post_backfill_differences"] == []
    assert report["parity"] is True


def test_same_batch_replay_is_idempotent(report) -> None:
    assert report["replay_skipped_batches"] > 0, "replay must hit the batch registry"
    assert report["replay_idempotent"] is True


def test_beyond_lookback_miss_is_demonstrated_before_backfill(report) -> None:
    assert report["pre_backfill_miss_demonstrated"] is True
    assert any(
        "lgl_" in difference or "prs_" in difference
        for difference in report["pre_backfill_differences"]
    ), "the held-back batch must visibly distort at least one governed interface"


def test_backfill_window_is_bounded(report) -> None:
    start, end = report["backfill_window"]
    assert start < end
    assert start == report["phases"]["held_back_day"]


def test_backfill_log_records_reason_and_operator() -> None:
    log_path = ROOT / "artifacts" / "plan2" / "backfill-log.jsonl"
    assert log_path.exists()
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert records, "backfill must be recorded"
    for record in records:
        assert record["reason"] and record["operator"]
        assert record["backfill_start"] < record["backfill_end"]
