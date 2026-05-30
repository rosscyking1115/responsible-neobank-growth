"""Render Cloud Storage upload commands from a cloud export manifest."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_EXPORT_MANIFEST_PATH = Path("data/cloud_export/demo/manifest.json")
BUCKET_ENV_REF = "${NEOBANK_GCS_RAW_BUCKET}"
PREFIX_ENV_REF = "${NEOBANK_GCS_RAW_PREFIX}"


@dataclass(frozen=True)
class CloudExportTable:
    name: str
    file: str
    row_count: int
    size_bytes: int


@dataclass(frozen=True)
class CloudExportManifest:
    manifest_version: int
    schema_version: str
    profile: str
    source_format: str
    tables: tuple[CloudExportTable, ...]


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Export manifest field '{key}' must be a non-empty string.")
    return value


def _load_table(payload: dict[str, Any]) -> CloudExportTable:
    return CloudExportTable(
        name=_require_string(payload, "name"),
        file=_require_string(payload, "file"),
        row_count=int(payload.get("row_count", 0)),
        size_bytes=int(payload.get("size_bytes", 0)),
    )


def load_export_manifest(path: Path = DEFAULT_EXPORT_MANIFEST_PATH) -> CloudExportManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tables_payload = payload.get("tables")
    if not isinstance(tables_payload, list) or not tables_payload:
        raise ValueError("Export manifest field 'tables' must be a non-empty list.")
    tables = tuple(_load_table(table) for table in tables_payload)
    table_files = [table.file for table in tables]
    if len(table_files) != len(set(table_files)):
        raise ValueError("Export manifest table files must be unique.")
    if any(table.row_count <= 0 for table in tables):
        raise ValueError("Export manifest table row counts must be positive.")
    if any(table.size_bytes <= 0 for table in tables):
        raise ValueError("Export manifest table file sizes must be positive.")
    return CloudExportManifest(
        manifest_version=int(payload.get("manifest_version", 0)),
        schema_version=_require_string(payload, "schema_version"),
        profile=_require_string(payload, "profile"),
        source_format=_require_string(payload, "format"),
        tables=tables,
    )


def _destination_uri(table: CloudExportTable, bucket: str, prefix: str) -> str:
    cleaned_prefix = prefix.strip("/")
    return f"gs://{bucket}/{cleaned_prefix}/{table.file}"


def render_gcs_upload_command(
    table: CloudExportTable,
    export_dir: Path,
    bucket: str = BUCKET_ENV_REF,
    prefix: str = PREFIX_ENV_REF,
) -> str:
    source = (export_dir / table.file).as_posix()
    destination = _destination_uri(table, bucket, prefix)
    return f"gcloud storage cp {source} {destination}"


def validate_export_files(manifest: CloudExportManifest, export_dir: Path) -> None:
    missing = [table.file for table in manifest.tables if not (export_dir / table.file).exists()]
    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(f"Export manifest references missing files: {joined}.")


def render_upload_plan(
    manifest: CloudExportManifest,
    export_dir: Path,
    bucket: str = BUCKET_ENV_REF,
    prefix: str = PREFIX_ENV_REF,
) -> str:
    total_rows = sum(table.row_count for table in manifest.tables)
    total_size = sum(table.size_bytes for table in manifest.tables)
    lines = [
        "# Cloud Storage Raw Upload Plan",
        "",
        f"Manifest version: {manifest.manifest_version}",
        f"Schema version: {manifest.schema_version}",
        f"Profile: {manifest.profile}",
        f"Tables: {len(manifest.tables)}",
        f"Rows: {total_rows:,}",
        f"Bytes: {total_size:,}",
        "",
        "Set these environment variables before running the commands:",
        "",
        "- `NEOBANK_GCS_RAW_BUCKET`",
        "- `NEOBANK_GCS_RAW_PREFIX`",
        "",
        "```bash",
    ]
    lines.extend(
        render_gcs_upload_command(table, export_dir, bucket=bucket, prefix=prefix)
        for table in manifest.tables
    )
    lines.extend(["```", ""])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Cloud Storage upload commands.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_EXPORT_MANIFEST_PATH)
    parser.add_argument("--bucket", default=BUCKET_ENV_REF)
    parser.add_argument("--prefix", default=PREFIX_ENV_REF)
    parser.add_argument(
        "--skip-file-check",
        action="store_true",
        help="Render commands without checking that local parquet files exist.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = load_export_manifest(args.manifest)
    export_dir = args.manifest.parent
    if not args.skip_file_check:
        validate_export_files(manifest, export_dir)
    print(render_upload_plan(manifest, export_dir, bucket=args.bucket, prefix=args.prefix))


if __name__ == "__main__":
    main()
