"""Build the synthetic event benchmark dataset release tree.

Assembles ``dataset/`` deterministically from generated simulator output plus
the committed contracts and configs, computes SHA256SUMS, and writes a build
manifest. Data files are never hand-edited — they come straight from the
generator. The ``tiny`` config is small and committed; the ``standard`` config
is built on demand for upload (gitignored) and recorded in the manifest.

Usage:
    python -m tools.release.build_dataset --profiles tiny            # committed tree
    python -m tools.release.build_dataset --profiles tiny standard   # full, for upload
"""

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "dataset"
GENERATED = ROOT / "data" / "generated"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_profile(profile: str) -> dict:
    src = GENERATED / profile
    if not (src / "manifest.json").exists():
        raise FileNotFoundError(
            f"generate {profile} first: "
            f"uv run python -m src.event_simulator.cli generate --profile {profile} "
            f"--output data/generated/{profile}"
        )
    dst_data = DATASET / "data" / profile
    dst_truth = DATASET / "truth"
    dst_data.mkdir(parents=True, exist_ok=True)
    dst_truth.mkdir(parents=True, exist_ok=True)

    # Batches -> data/<profile>/; split valid vs malformed by scenario is done
    # downstream, so we ship the raw delivery batches plus the truth manifest.
    for batch in sorted((src / "batches").glob("*.jsonl")):
        shutil.copy2(batch, dst_data / batch.name)

    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    truth_out = dst_truth / f"{profile}-manifest.json"
    truth_out.write_text(
        json.dumps(manifest["truth"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    return {
        "profile": profile,
        "logical_checksum": manifest["logical_checksum"],
        "batch_count": len(manifest["batches"]),
        "delivery_count": manifest["truth"]["delivery_count"],
    }


def _copy_static() -> None:
    (DATASET / "schemas").mkdir(parents=True, exist_ok=True)
    (DATASET / "configs").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "contracts" / "events" / "event-envelope.schema.json",
                 DATASET / "schemas" / "event-envelope.schema.json")
    shutil.copy2(ROOT / "contracts" / "events" / "registry.yml",
                 DATASET / "schemas" / "registry.yml")
    payloads = DATASET / "schemas" / "event-payloads"
    payloads.mkdir(exist_ok=True)
    for schema in (ROOT / "contracts" / "events").rglob("v*/*.schema.json"):
        shutil.copy2(schema, payloads / f"{schema.parent.name}-{schema.name}")
    for profile in ("tiny", "standard"):
        cfg = ROOT / "config" / "simulator" / f"{profile}.yml"
        if cfg.exists():
            shutil.copy2(cfg, DATASET / "configs" / f"{profile}.yml")


def _write_checksums(profiles: list[str]) -> None:
    lines = []
    for path in sorted(DATASET.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS", "build-manifest.json"}:
            continue  # build-manifest carries a timestamp and summarises the build
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(DATASET).as_posix()
        lines.append(f"{_sha256(path)}  {rel}")
    (DATASET / "checksums").mkdir(exist_ok=True)
    (DATASET / "checksums" / "SHA256SUMS").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def build(profiles: list[str]) -> dict:
    _copy_static()
    profile_records = [_copy_profile(p) for p in profiles]
    _write_checksums(profiles)
    manifest = {
        "built_at_utc": datetime.now(UTC).isoformat(),
        "release_branch": "bigquery-only",
        "generator_version": "0.1.0",
        "profiles": profile_records,
        "licence": {"code": "MIT", "data": "CC-BY-4.0 (proposed; confirm at publication)"},
        "note": "Data files are generator output, never hand-edited. "
                "standard data is built on demand and uploaded, not committed.",
    }
    (DATASET / "build-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", nargs="+", default=["tiny"])
    args = parser.parse_args(argv)
    manifest = build(args.profiles)
    print(json.dumps(manifest["profiles"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
