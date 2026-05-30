from __future__ import annotations

from pathlib import Path

from data_generator.config import GeneratorConfig
from src.cloud.bigquery_verify_plan import (
    expected_row_counts,
    render_bq_query_command,
    render_raw_row_count_sql,
    render_table_count_select,
    render_verification_plan,
)
from src.cloud.export import export_cloud_dataset
from src.cloud.gcp_load_plan import load_manifest
from src.cloud.gcs_upload_plan import load_export_manifest


def test_expected_row_counts_reads_export_manifest(tmp_path: Path) -> None:
    export_cloud_dataset(GeneratorConfig(users=120, months=1, seed=19), tmp_path, "demo")
    export_manifest = load_export_manifest(tmp_path / "manifest.json")

    counts = expected_row_counts(export_manifest)

    assert counts["users"] == 120
    assert counts["experiment_assignments"] == 120
    assert counts["transactions"] > 0


def test_render_table_count_select_uses_quoted_bigquery_ref() -> None:
    sql = render_table_count_select(
        "neobank-growth-platform-ross",
        "neobank_raw",
        "users",
        expected_rows=5_000,
    )

    assert "COUNT(*) AS actual_rows" in sql
    assert "5000 AS expected_rows" in sql
    assert "COUNT(*) = 5000 AS passed" in sql
    assert "FROM `neobank-growth-platform-ross.neobank_raw.users`" in sql


def test_render_raw_row_count_sql_covers_raw_manifest_tables() -> None:
    manifest = load_manifest()

    sql = render_raw_row_count_sql(
        manifest,
        "neobank-growth-platform-ross",
        "neobank_raw",
        {"users": 5_000},
    )

    assert sql.count("SELECT ") == 13
    assert "SELECT 'users' AS table_name" in sql
    assert "SELECT 'transactions' AS table_name" in sql
    assert "ORDER BY table_name" in sql


def test_render_bq_query_command_is_powershell_safe() -> None:
    command = render_bq_query_command(
        "SELECT 'users' AS table_name FROM `neobank-growth-platform-ross.neobank_raw.users`"
    )

    assert command.startswith("bq query --use_legacy_sql=false '")
    assert command.endswith("'")
    assert "SELECT ''users'' AS table_name" in command
    assert "`neobank-growth-platform-ross.neobank_raw.users`" in command


def test_render_verification_plan_includes_ls_and_row_count_query() -> None:
    manifest = load_manifest()

    plan = render_verification_plan(
        manifest,
        "neobank-growth-platform-ross",
        "neobank_raw",
        {"users": 5_000},
    )

    assert "BigQuery Raw Verification Plan" in plan
    assert "bq ls neobank-growth-platform-ross:neobank_raw" in plan
    assert "bq query --use_legacy_sql=false" in plan
    assert "COUNT(*) = 5000 AS passed" in plan
