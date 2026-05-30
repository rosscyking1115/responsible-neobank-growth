from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.cloud.bigquery_score_load_plan import (
    build_score_load_plan,
    destination_uri,
    render_dataset_command,
    render_load_command,
    render_plan_dataset_command,
    render_score_load_plan,
    render_upload_command,
    render_verification_command,
    score_partition_path,
    table_ref,
    validate_score_file,
)


def test_score_partition_path_matches_batch_scoring_contract() -> None:
    path = score_partition_path(Path("artifacts/scoring/activation"), date(2025, 6, 30))

    assert path.as_posix() == (
        "artifacts/scoring/activation/score_date=2025-06-30/customer_scores_daily.parquet"
    )


def test_destination_uri_keeps_score_date_partition() -> None:
    uri = destination_uri(
        bucket="neobank-growth-platform-ross-raw",
        prefix="neobank/scoring/activation/",
        score_date=date(2025, 6, 30),
    )

    assert uri == (
        "gs://neobank-growth-platform-ross-raw/neobank/scoring/activation/"
        "score_date=2025-06-30/customer_scores_daily.parquet"
    )


def test_table_ref_uses_bigquery_cli_format() -> None:
    assert (
        table_ref("neobank-growth-platform-ross", "neobank_ml")
        == "neobank-growth-platform-ross:neobank_ml.customer_scores_daily"
    )


def test_render_commands_cover_upload_dataset_load_and_verification() -> None:
    plan = build_score_load_plan(
        score_date=date(2025, 6, 30),
        project="neobank-growth-platform-ross",
        dataset="neobank_ml",
        location="EU",
        bucket="neobank-growth-platform-ross-raw",
        prefix="neobank/scoring/activation",
    )

    upload = render_upload_command(plan)
    dataset = render_dataset_command(
        project="neobank-growth-platform-ross",
        dataset="neobank_ml",
        location="EU",
    )
    plan_dataset = render_plan_dataset_command(plan, location="EU")
    load = render_load_command(plan, location="EU")
    verify = render_verification_command(plan)

    assert upload.startswith("gcloud storage cp artifacts/scoring/activation/")
    assert dataset == (
        "bq --location=EU mk --dataset --if_not_exists "
        "neobank-growth-platform-ross:neobank_ml"
    )
    assert plan_dataset == dataset
    assert "--time_partitioning_field=score_date" in load
    assert "--clustering_fields=model_version,decision,region" in load
    assert "neobank-growth-platform-ross:neobank_ml.customer_scores_daily" in load
    assert "COUNTIF(decision = ''target'')" in verify
    assert "DATE ''2025-06-30''" in verify


def test_render_score_load_plan_lists_environment_variables() -> None:
    plan = build_score_load_plan(score_date=date(2025, 6, 30))

    rendered = render_score_load_plan(plan)

    assert "BigQuery Activation Score Load Plan" in rendered
    assert "`NEOBANK_BQ_ML_DATASET`" in rendered
    assert "`NEOBANK_GCS_SCORING_PREFIX`" in rendered
    assert "bq --location=${NEOBANK_BQ_LOCATION} load" in rendered
    assert "bq query --use_legacy_sql=false" in rendered


def test_render_score_load_plan_uses_explicit_destination_refs() -> None:
    plan = build_score_load_plan(
        score_date=date(2025, 6, 30),
        project="neobank-growth-platform-ross",
        dataset="neobank_ml",
        location="EU",
        bucket="neobank-growth-platform-ross-raw",
        prefix="neobank/scoring/activation",
    )

    rendered = render_score_load_plan(plan)

    assert "neobank-growth-platform-ross:neobank_ml" in rendered
    assert "bq --location=EU load" in rendered
    assert "${GCP_PROJECT_ID}:${NEOBANK_BQ_ML_DATASET}" not in rendered


def test_validate_score_file_raises_for_missing_extract(tmp_path: Path) -> None:
    plan = build_score_load_plan(score_date=date(2025, 6, 30), score_dir=tmp_path)

    with pytest.raises(FileNotFoundError, match="Generate it first"):
        validate_score_file(plan)
