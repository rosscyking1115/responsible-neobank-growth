"""Dataset package validation (Plan 4, Task 6).

The committed dataset tree must be internally consistent: checksums match,
required files present, truth manifest agrees with the shipped batches, the
data card carries the mandatory boundaries, and the licence is stated.
"""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "dataset"

pytestmark = pytest.mark.skipif(
    not (DATASET / "build-manifest.json").exists(),
    reason="dataset tree not built: uv run python -m tools.release.build_dataset --profiles tiny",
)


def test_required_files_present() -> None:
    for rel in [
        "README.md",
        "build-manifest.json",
        "checksums/SHA256SUMS",
        "schemas/event-envelope.schema.json",
        "schemas/registry.yml",
        "configs/tiny.yml",
        "truth/tiny-manifest.json",
        "examples/validate_truth.py",
    ]:
        assert (DATASET / rel).exists(), f"missing dataset file: {rel}"
    assert list((DATASET / "data" / "tiny").glob("*.jsonl")), "tiny data batches missing"


def test_checksums_match() -> None:
    sums = (DATASET / "checksums" / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    recorded = {}
    for line in sums:
        digest, rel = line.split("  ", 1)
        recorded[rel] = digest
    for path in DATASET.rglob("*"):
        if (
            not path.is_file()
            or path.name in {"SHA256SUMS", "build-manifest.json"}
            or "__pycache__" in path.parts
        ):
            continue
        rel = path.relative_to(DATASET).as_posix()
        assert rel in recorded, f"file not in SHA256SUMS: {rel}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == recorded[rel], (
            f"checksum mismatch: {rel}"
        )


def test_truth_manifest_agrees_with_shipped_batches() -> None:
    truth = json.loads((DATASET / "truth" / "tiny-manifest.json").read_text(encoding="utf-8"))
    events = []
    for batch in sorted((DATASET / "data" / "tiny").glob("*.jsonl")):
        for line in batch.read_text(encoding="utf-8").splitlines():
            if line:
                events.append(json.loads(line))
    # delivery_count = valid + quarantined; valid = unique_business_events + duplicates.
    assert len(events) == truth["delivery_count"]
    assert truth["delivery_count"] == (
        truth["unique_business_events"]
        + truth["expected_duplicates"]
        + truth["expected_quarantined"]
    )


def test_data_card_states_boundaries_and_licence() -> None:
    card = (DATASET / "README.md").read_text(encoding="utf-8").lower()
    for marker in [
        "synthetic", "no affiliation", "prohibited", "limitations",
        "cc-by-4.0", "not calibrated", "monzo",
    ]:
        assert marker in card, f"data card missing: {marker}"


def test_build_manifest_records_provenance() -> None:
    manifest = json.loads((DATASET / "build-manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_branch"] == "bigquery-only"
    assert manifest["generator_version"]
    tiny = next(p for p in manifest["profiles"] if p["profile"] == "tiny")
    assert tiny["logical_checksum"] and tiny["delivery_count"] > 0


def test_no_standard_data_committed() -> None:
    """The large standard profile data must not be in the committed tree."""
    import subprocess

    tracked = subprocess.check_output(
        ["git", "ls-files", "dataset/"], cwd=ROOT, text=True
    ).splitlines()
    offenders = [t for t in tracked if t.startswith("dataset/data/standard/")]
    assert offenders == [], f"standard data must not be committed: {offenders[:3]}"
