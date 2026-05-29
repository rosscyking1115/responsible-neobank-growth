from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.cloud.gcp_load_plan import load_manifest, render_bq_load_command, render_load_plan


def test_default_manifest_covers_all_raw_generator_outputs() -> None:
    manifest = load_manifest()

    assert len(manifest.tables) == 13
    assert {table.file for table in manifest.tables} == {
        "activation_ground_truth.parquet",
        "experiment_assignments.parquet",
        "experiment_ground_truth.parquet",
        "feature_events.parquet",
        "pricing_exposures.parquet",
        "pricing_offer_catalog.parquet",
        "pricing_outcomes.parquet",
        "referrals.parquet",
        "region_daily_signups.parquet",
        "sessions.parquet",
        "support_contacts.parquet",
        "transactions.parquet",
        "users.parquet",
    }


def test_render_bq_load_command_includes_partition_and_clustering() -> None:
    manifest = load_manifest()
    users = next(table for table in manifest.tables if table.name == "users")

    command = render_bq_load_command(manifest, users)

    assert "--source_format=PARQUET" in command
    assert "--replace" in command
    assert "--time_partitioning_field=signup_date" in command
    assert "--clustering_fields=region,signup_channel,income_segment" in command
    assert "${GCP_PROJECT_ID}:${NEOBANK_BQ_RAW_DATASET}.users" in command
    assert "gs://${NEOBANK_GCS_RAW_BUCKET}/${NEOBANK_GCS_RAW_PREFIX}/users.parquet" in command


def test_render_bq_load_command_omits_partition_for_dimension_table() -> None:
    manifest = load_manifest()
    offers = next(table for table in manifest.tables if table.name == "pricing_offer_catalog")

    command = render_bq_load_command(manifest, offers)

    assert "--time_partitioning_field" not in command
    assert "--clustering_fields=product_area,offer_type" in command


def test_render_load_plan_lists_required_environment_variables() -> None:
    manifest = load_manifest()

    plan = render_load_plan(manifest)

    assert "BigQuery Raw Load Plan" in plan
    assert "`GCP_PROJECT_ID`" in plan
    assert "`NEOBANK_GCS_RAW_PREFIX`" in plan
    assert "bq --location=${NEOBANK_BQ_LOCATION} load" in plan


def test_manifest_rejects_duplicate_table_names(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    payload = json.loads(Path("cloud/gcp/raw_bigquery_manifest.json").read_text(encoding="utf-8"))
    payload["tables"][1]["name"] = payload["tables"][0]["name"]
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unique"):
        load_manifest(manifest_path)
