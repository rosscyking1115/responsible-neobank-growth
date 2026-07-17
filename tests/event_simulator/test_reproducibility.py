"""Reproducibility tests.

Repeated runs in separate directories must produce identical logical content
(batch files and checksums); environment metadata is declared non-semantic and
excluded. Comparison uses content, never file timestamps.
"""

import json
from pathlib import Path

import pytest

from src.event_simulator.cli import main as cli_main
from src.event_simulator.config import load_config
from src.event_simulator.generator import generate_valid_events
from src.event_simulator.scenarios import apply_faults
from src.event_simulator.writers import compare_outputs, logical_checksum, write_output

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT / "config" / "simulator" / "tiny.yml")


@pytest.fixture(scope="module")
def two_runs(tmp_path_factory):
    out_a = tmp_path_factory.mktemp("tiny-a")
    out_b = tmp_path_factory.mktemp("tiny-b")
    for out in (out_a, out_b):
        faulted = apply_faults(generate_valid_events(CONFIG), CONFIG)
        write_output(faulted, CONFIG, out)
    return out_a, out_b


def test_repeated_runs_match_logical_checksums(two_runs) -> None:
    out_a, out_b = two_runs
    assert logical_checksum(out_a) == logical_checksum(out_b)
    assert compare_outputs(out_a, out_b) == []


def test_batch_files_are_byte_identical(two_runs) -> None:
    out_a, out_b = two_runs
    files_a = sorted(p.name for p in (out_a / "batches").glob("*.jsonl"))
    files_b = sorted(p.name for p in (out_b / "batches").glob("*.jsonl"))
    assert files_a == files_b and files_a
    for name in files_a:
        assert (out_a / "batches" / name).read_bytes() == (
            out_b / "batches" / name
        ).read_bytes()


def test_manifest_batches_reconcile_to_content(two_runs) -> None:
    out_a, _ = two_runs
    with open(out_a / "manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)
    batches = manifest["batches"]
    assert batches, "output must be partitioned into ingestion-date batches"
    total_rows = 0
    for batch in batches:
        path = out_a / batch["path"]
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == batch["row_count"]
        total_rows += batch["row_count"]
        assert batch["batch_id"] and batch["checksum"]
        assert batch["min_ingested_at"] <= batch["max_ingested_at"]
    assert total_rows == manifest["truth"]["delivery_count"]


def test_environment_metadata_is_recorded_but_non_semantic(two_runs) -> None:
    out_a, _ = two_runs
    with open(out_a / "manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)
    environment = manifest["environment"]
    assert environment["python"] and environment["platform"]
    assert "git_commit" in environment
    assert manifest["logical_checksum"], "logical checksum must exist"


def test_tampered_output_is_detected(two_runs, tmp_path) -> None:
    import shutil

    out_a, out_b = two_runs
    tampered = tmp_path / "tampered"
    shutil.copytree(out_b, tampered)
    target = sorted((tampered / "batches").glob("*.jsonl"))[0]
    lines = target.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    record["payload"]["amount_minor"] = record["payload"].get("amount_minor", 0) + 1
    lines[0] = json.dumps(record, sort_keys=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    differences = compare_outputs(out_a, tampered)
    assert differences, "a single altered value must change the logical checksum"


def test_cli_generate_and_compare(two_runs, tmp_path) -> None:
    out_a, _ = two_runs
    cli_out = tmp_path / "cli-run"
    assert cli_main(["generate", "--profile", "tiny", "--output", str(cli_out)]) == 0
    assert (cli_out / "manifest.json").exists()
    assert cli_main(["compare", "--left", str(out_a), "--right", str(cli_out)]) == 0
    # Comparing against a tampered/other directory must exit nonzero.
    empty = tmp_path / "empty"
    empty.mkdir()
    assert cli_main(["compare", "--left", str(out_a), "--right", str(empty)]) == 1
