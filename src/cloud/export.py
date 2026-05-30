"""Create a cloud-ready raw parquet export with a machine-readable manifest."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import polars as pl

from data_generator.config import GeneratorConfig
from data_generator.generate import build_dataset, write_dataset
from src.cloud.config import load_cloud_config

SCHEMA_VERSION = "2026-05-30"
PROFILE_DEFAULTS = {
    "demo": {"users": 5_000, "months": 6},
    "portfolio": {"users": 50_000, "months": 12},
}


def _schema_for(frame: pl.DataFrame) -> dict[str, str]:
    return {name: str(dtype) for name, dtype in frame.schema.items()}


def _table_manifest(name: str, frame: pl.DataFrame, output_dir: Path) -> dict[str, Any]:
    file_path = output_dir / f"{name}.parquet"
    return {
        "name": name,
        "file": file_path.name,
        "row_count": frame.height,
        "column_count": len(frame.columns),
        "columns": _schema_for(frame),
        "size_bytes": file_path.stat().st_size,
    }


def build_export_manifest(
    frames: dict[str, pl.DataFrame],
    output_dir: Path,
    config: GeneratorConfig,
    profile: str,
) -> dict[str, Any]:
    return {
        "manifest_version": 1,
        "schema_version": SCHEMA_VERSION,
        "exported_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "profile": profile,
        "format": "parquet",
        "generator_config": {
            key: value.isoformat() if isinstance(value, date) else value
            for key, value in asdict(config).items()
        },
        "tables": [_table_manifest(name, frame, output_dir) for name, frame in frames.items()],
    }


def export_cloud_dataset(config: GeneratorConfig, output_dir: Path, profile: str) -> dict[str, Any]:
    frames = build_dataset(config)
    write_dataset(frames, output_dir)
    manifest = build_export_manifest(frames, output_dir, config, profile)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export synthetic data for Cloud Storage/BigQuery."
    )
    parser.add_argument("--profile", choices=sorted(PROFILE_DEFAULTS), default="demo")
    parser.add_argument("--users", type=int)
    parser.add_argument("--months", type=int)
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2025, 1, 1))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def _generator_config(args: argparse.Namespace) -> GeneratorConfig:
    defaults = PROFILE_DEFAULTS[args.profile]
    return GeneratorConfig(
        users=args.users or defaults["users"],
        months=args.months or defaults["months"],
        start_date=args.start_date,
        seed=args.seed,
    )


def main() -> None:
    args = parse_args()
    cloud_config = load_cloud_config()
    output_dir = args.output_dir or cloud_config.cloud_export_dir
    manifest = export_cloud_dataset(_generator_config(args), output_dir, args.profile)
    print(f"Wrote cloud export to {output_dir.resolve()}")
    print(f"Wrote manifest to {(output_dir / 'manifest.json').resolve()}")
    for table in manifest["tables"]:
        print(f"- {table['name']}: {table['row_count']:,} rows")


if __name__ == "__main__":
    main()
