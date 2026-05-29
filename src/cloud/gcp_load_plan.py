"""Render BigQuery raw-load commands from a versioned Cloud Storage manifest."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST_PATH = Path("cloud/gcp/raw_bigquery_manifest.json")


@dataclass(frozen=True)
class RawTableLoad:
    name: str
    file: str
    grain: str
    partition_field: str | None
    cluster_fields: tuple[str, ...]
    write_disposition: str


@dataclass(frozen=True)
class BigQueryRawManifest:
    manifest_version: int
    description: str
    project_env_var: str
    dataset_env_var: str
    location_env_var: str
    bucket_env_var: str
    prefix_env_var: str
    source_format: str
    tables: tuple[RawTableLoad, ...]


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Manifest field '{key}' must be a non-empty string.")
    return value


def _load_table(payload: dict[str, Any]) -> RawTableLoad:
    partition_field = payload.get("partition_field")
    if partition_field is not None and not isinstance(partition_field, str):
        raise ValueError("Table field 'partition_field' must be a string or null.")
    cluster_fields = payload.get("cluster_fields", [])
    if not isinstance(cluster_fields, list) or not all(
        isinstance(field, str) and field for field in cluster_fields
    ):
        raise ValueError("Table field 'cluster_fields' must be a list of strings.")
    return RawTableLoad(
        name=_require_string(payload, "name"),
        file=_require_string(payload, "file"),
        grain=_require_string(payload, "grain"),
        partition_field=partition_field,
        cluster_fields=tuple(cluster_fields),
        write_disposition=_require_string(payload, "write_disposition"),
    )


def load_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> BigQueryRawManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tables_payload = payload.get("tables")
    if not isinstance(tables_payload, list) or not tables_payload:
        raise ValueError("Manifest field 'tables' must be a non-empty list.")
    tables = tuple(_load_table(table) for table in tables_payload)
    table_names = [table.name for table in tables]
    if len(table_names) != len(set(table_names)):
        raise ValueError("Manifest table names must be unique.")
    return BigQueryRawManifest(
        manifest_version=int(payload.get("manifest_version", 0)),
        description=_require_string(payload, "description"),
        project_env_var=_require_string(payload, "project_env_var"),
        dataset_env_var=_require_string(payload, "dataset_env_var"),
        location_env_var=_require_string(payload, "location_env_var"),
        bucket_env_var=_require_string(payload, "bucket_env_var"),
        prefix_env_var=_require_string(payload, "prefix_env_var"),
        source_format=_require_string(payload, "source_format"),
        tables=tables,
    )


def _env_ref(name: str) -> str:
    return "${" + name + "}"


def _source_uri(manifest: BigQueryRawManifest, table: RawTableLoad) -> str:
    bucket = _env_ref(manifest.bucket_env_var)
    prefix = _env_ref(manifest.prefix_env_var)
    return f"gs://{bucket}/{prefix}/{table.file}"


def render_bq_load_command(manifest: BigQueryRawManifest, table: RawTableLoad) -> str:
    project = _env_ref(manifest.project_env_var)
    dataset = _env_ref(manifest.dataset_env_var)
    location = _env_ref(manifest.location_env_var)
    command_parts = [
        "bq",
        f"--location={location}",
        "load",
        f"--source_format={manifest.source_format}",
        "--replace" if table.write_disposition == "WRITE_TRUNCATE" else "--append_table",
    ]
    if table.partition_field:
        command_parts.append(f"--time_partitioning_field={table.partition_field}")
    if table.cluster_fields:
        command_parts.append(f"--clustering_fields={','.join(table.cluster_fields)}")
    command_parts.extend(
        [
            f"{project}:{dataset}.{table.name}",
            _source_uri(manifest, table),
        ]
    )
    return " ".join(command_parts)


def render_load_plan(manifest: BigQueryRawManifest) -> str:
    lines = [
        "# BigQuery Raw Load Plan",
        "",
        f"Manifest version: {manifest.manifest_version}",
        "",
        "Set these environment variables before running the commands:",
        "",
        f"- `{manifest.project_env_var}`",
        f"- `{manifest.dataset_env_var}`",
        f"- `{manifest.location_env_var}`",
        f"- `{manifest.bucket_env_var}`",
        f"- `{manifest.prefix_env_var}`",
        "",
        "```bash",
    ]
    lines.extend(render_bq_load_command(manifest, table) for table in manifest.tables)
    lines.extend(["```", ""])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render BigQuery raw load commands.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(render_load_plan(load_manifest(args.manifest)))


if __name__ == "__main__":
    main()
