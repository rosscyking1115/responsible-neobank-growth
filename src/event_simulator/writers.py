"""Deterministic batch writer and content comparison (Plan 2, Tasks 4 and 6.1).

Deliveries are written as immutable, partition-addressable daily batches
(JSONL, sorted, sorted-key JSON) plus a run manifest carrying the truth
manifest, per-batch metadata and a logical checksum. Environment metadata is
recorded for the reproducibility contract but excluded from logical
comparison; nothing here depends on wall-clock time or file timestamps.
"""

import hashlib
import json
import platform
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from src.event_simulator.config import SimulatorConfig


def _canonical_line(event: dict) -> str:
    return json.dumps(event, sort_keys=True)


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _environment() -> dict:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_commit": _git_commit(),
        "packages": {
            "jsonschema": version("jsonschema"),
            "pyyaml": version("pyyaml"),
        },
    }


def write_output(faulted, config: SimulatorConfig, output_dir: Path) -> dict:
    """Write daily ingestion batches plus manifest.json; returns a summary."""
    output_dir = Path(output_dir)
    batches_dir = output_dir / "batches"
    batches_dir.mkdir(parents=True, exist_ok=True)

    by_day: dict[str, list[dict]] = {}
    for event in faulted.deliveries:
        by_day.setdefault(event["ingested_at"][:10], []).append(event)

    batches: list[dict] = []
    for day in sorted(by_day):
        events = sorted(by_day[day], key=lambda e: (e["ingested_at"], e["event_id"]))
        content = "\n".join(_canonical_line(e) for e in events) + "\n"
        relative = f"batches/ingest-{day}.jsonl"
        (output_dir / relative).write_text(content, encoding="utf-8", newline="\n")
        batches.append(
            {
                "batch_id": f"batch-{day}",
                "path": relative,
                "row_count": len(events),
                "min_occurred_at": min(e["occurred_at"] for e in events),
                "max_occurred_at": max(e["occurred_at"] for e in events),
                "min_ingested_at": events[0]["ingested_at"],
                "max_ingested_at": events[-1]["ingested_at"],
                "checksum": hashlib.sha256(content.encode()).hexdigest(),
                "schema_registry_version": 1,
                "truth_manifest": "manifest.json#truth",
            }
        )

    logical = hashlib.sha256(
        "".join(batch["checksum"] for batch in batches).encode()
    ).hexdigest()

    manifest = {
        "logical_checksum": logical,
        "batches": batches,
        "truth": faulted.manifest,
        "environment": _environment(),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return {"batches": len(batches), "deliveries": sum(b["row_count"] for b in batches),
            "logical_checksum": logical}


def logical_checksum(output_dir: Path) -> str:
    """Recompute the logical checksum from batch file content on disk."""
    output_dir = Path(output_dir)
    checksums = []
    for path in sorted((output_dir / "batches").glob("*.jsonl")):
        checksums.append(hashlib.sha256(path.read_bytes()).hexdigest())
    return hashlib.sha256("".join(checksums).encode()).hexdigest()


def compare_outputs(left: Path, right: Path) -> list[str]:
    """Compare two run outputs logically; returns one message per difference."""
    left, right = Path(left), Path(right)
    differences: list[str] = []
    for side, path in (("left", left), ("right", right)):
        if not (path / "manifest.json").exists():
            differences.append(f"{side}: missing manifest.json in {path}")
    if differences:
        return differences

    if logical_checksum(left) != logical_checksum(right):
        differences.append("logical checksum mismatch between batch contents")

    with open(left / "manifest.json", encoding="utf-8") as f:
        manifest_left = json.load(f)
    with open(right / "manifest.json", encoding="utf-8") as f:
        manifest_right = json.load(f)
    for manifest in (manifest_left, manifest_right):
        manifest.pop("environment", None)  # declared non-semantic
    if manifest_left != manifest_right:
        differences.append("truth/batch manifests differ (excluding environment)")
    return differences
