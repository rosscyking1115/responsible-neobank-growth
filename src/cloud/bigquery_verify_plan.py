"""Render PowerShell-safe BigQuery raw-table verification commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.cloud.gcp_load_plan import DEFAULT_MANIFEST_PATH, BigQueryRawManifest, load_manifest
from src.cloud.gcs_upload_plan import CloudExportManifest, load_export_manifest

DEFAULT_EXPECTED_EXPORT_MANIFEST_PATH = Path("data/cloud_export/demo/manifest.json")


def _table_ref(project_id: str, dataset: str, table_name: str) -> str:
    return f"`{project_id}.{dataset}.{table_name}`"


def expected_row_counts(export_manifest: CloudExportManifest) -> dict[str, int]:
    return {table.name: table.row_count for table in export_manifest.tables}


def render_table_count_select(
    project_id: str,
    dataset: str,
    table_name: str,
    expected_rows: int | None = None,
) -> str:
    expected_sql = "NULL" if expected_rows is None else str(expected_rows)
    passed_sql = "TRUE" if expected_rows is None else f"COUNT(*) = {expected_rows}"
    return (
        f"SELECT '{table_name}' AS table_name, "
        f"COUNT(*) AS actual_rows, "
        f"{expected_sql} AS expected_rows, "
        f"{passed_sql} AS passed "
        f"FROM {_table_ref(project_id, dataset, table_name)}"
    )


def render_raw_row_count_sql(
    raw_manifest: BigQueryRawManifest,
    project_id: str,
    dataset: str,
    expected_counts: dict[str, int] | None = None,
) -> str:
    counts = expected_counts or {}
    selects = [
        render_table_count_select(project_id, dataset, table.name, counts.get(table.name))
        for table in raw_manifest.tables
    ]
    return " UNION ALL ".join(selects) + " ORDER BY table_name"


def render_bq_query_command(sql: str) -> str:
    powershell_sql = sql.replace("'", "''")
    return f"bq query --use_legacy_sql=false '{powershell_sql}'"


def render_verification_plan(
    raw_manifest: BigQueryRawManifest,
    project_id: str,
    dataset: str,
    expected_counts: dict[str, int] | None = None,
) -> str:
    sql = render_raw_row_count_sql(raw_manifest, project_id, dataset, expected_counts)
    lines = [
        "# BigQuery Raw Verification Plan",
        "",
        f"Project: {project_id}",
        f"Dataset: {dataset}",
        f"Tables: {len(raw_manifest.tables)}",
        "",
        "List loaded raw tables:",
        "",
        "```powershell",
        f"bq ls {project_id}:{dataset}",
        "```",
        "",
        "Verify raw row counts:",
        "",
        "```powershell",
        render_bq_query_command(sql),
        "```",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render BigQuery raw verification commands.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--dataset", default="neobank_raw")
    parser.add_argument("--raw-manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument(
        "--expected-export-manifest",
        type=Path,
        default=DEFAULT_EXPECTED_EXPORT_MANIFEST_PATH,
        help="Cloud export manifest with expected row counts.",
    )
    parser.add_argument(
        "--no-expected-counts",
        action="store_true",
        help="Render table existence/count checks without expected row-count comparisons.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_manifest = load_manifest(args.raw_manifest)
    counts = None
    if not args.no_expected_counts:
        counts = expected_row_counts(load_export_manifest(args.expected_export_manifest))
    print(render_verification_plan(raw_manifest, args.project, args.dataset, counts))


if __name__ == "__main__":
    main()
