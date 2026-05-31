from __future__ import annotations

from datetime import date
from pathlib import Path

from src.cloud.jobs.activation_score_load import (
    ActivationScoreLoadJobConfig,
    load_activation_score_load_job_config,
    run_activation_score_load_job,
    run_local_scoring_pipeline,
)
from src.cloud.jobs.score_monitoring import (
    load_score_monitoring_job_config,
    monitoring_result_from_row,
)


def test_activation_score_load_config_uses_env_contract(tmp_path: Path) -> None:
    config = load_activation_score_load_job_config(
        {
            "NEOBANK_SCORE_DATE": "2025-06-30",
            "GCP_PROJECT_ID": "neobank-growth-platform-ross",
            "NEOBANK_BQ_LOCATION": "EU",
            "NEOBANK_BQ_ML_DATASET": "neobank_ml",
            "NEOBANK_GCS_RAW_BUCKET": "neobank-growth-platform-ross-raw",
            "NEOBANK_GCS_SCORING_PREFIX": "neobank/scoring/activation",
            "NEOBANK_JOB_WORKDIR": str(tmp_path),
            "NEOBANK_JOB_USERS": "5000",
            "NEOBANK_JOB_MONTHS": "6",
        }
    )

    assert config.score_date == date(2025, 6, 30)
    assert config.gcs_uri == (
        "gs://neobank-growth-platform-ross-raw/neobank/scoring/activation/"
        "score_date=2025-06-30/customer_scores_daily.parquet"
    )
    assert config.score_path.as_posix().endswith(
        "artifacts/scoring/activation/score_date=2025-06-30/customer_scores_daily.parquet"
    )


def test_local_scoring_pipeline_runs_generator_dbt_train_and_score(tmp_path: Path) -> None:
    config = ActivationScoreLoadJobConfig(
        score_date=date(2025, 6, 30),
        project="neobank-growth-platform-ross",
        bq_location="EU",
        bq_dataset="neobank_ml",
        gcs_bucket="neobank-growth-platform-ross-raw",
        gcs_prefix="neobank/scoring/activation",
        working_dir=tmp_path,
        users=5000,
        months=6,
    )
    calls: list[list[str]] = []

    def fake_runner(args: list[str], *, env: dict[str, str] | None = None) -> None:
        calls.append(args)
        if args[0] == "dbt":
            assert env is not None
            assert env["NEOBANK_DUCKDB_PATH"] == config.duckdb_path.as_posix()

    run_local_scoring_pipeline(config, runner=fake_runner)

    assert calls[0][1:3] == ["-m", "data_generator.generate"]
    assert calls[1][:2] == ["dbt", "build"]
    assert calls[2][1:3] == ["-m", "src.modelling.run_activation_model"]
    assert calls[3][1:3] == ["-m", "src.modelling.batch_score_activation"]
    assert "--score-date" in calls[3]


def test_activation_score_load_job_orchestrates_local_cloud_steps(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = ActivationScoreLoadJobConfig(
        score_date=date(2025, 6, 30),
        project="neobank-growth-platform-ross",
        bq_location="EU",
        bq_dataset="neobank_ml",
        gcs_bucket="neobank-growth-platform-ross-raw",
        gcs_prefix="neobank/scoring/activation",
        working_dir=tmp_path,
        users=5000,
        months=6,
    )
    calls: list[str] = []

    monkeypatch.setattr(
        "src.cloud.jobs.activation_score_load.run_local_scoring_pipeline",
        lambda *_args, **_kwargs: calls.append("local"),
    )
    monkeypatch.setattr(
        "src.cloud.jobs.activation_score_load.upload_score_extract_to_gcs",
        lambda *_args, **_kwargs: calls.append("upload"),
    )
    monkeypatch.setattr(
        "src.cloud.jobs.activation_score_load.load_score_extract_to_bigquery",
        lambda *_args, **_kwargs: 5000,
    )

    result = run_activation_score_load_job(config)

    assert calls == ["local", "upload"]
    assert result.rows_loaded == 5000
    assert result.bq_table == "neobank-growth-platform-ross.neobank_ml.customer_scores_daily"


def test_score_monitoring_config_and_row_mapping() -> None:
    config = load_score_monitoring_job_config(
        {
            "NEOBANK_SCORE_DATE": "2025-06-30",
            "GCP_PROJECT_ID": "neobank-growth-platform-ross",
            "NEOBANK_BQ_LOCATION": "EU",
            "NEOBANK_BQ_ML_DATASET": "neobank_ml",
            "NEOBANK_BQ_MONITORING_DATASET": "neobank_monitoring",
            "NEOBANK_SCORE_MONITORING_MIN_ROWS": "5000",
            "NEOBANK_SCORE_MONITORING_FAIL_ON_WARN": "true",
        }
    )
    row = {
        "score_date": date(2025, 6, 30),
        "monitoring_status": "pass",
        "scored_users": 5000,
        "unique_users": 5000,
        "targeted_users": 1390,
        "targeting_rate": 0.278,
        "vulnerable_review_users": 191,
        "vulnerable_review_rate": 0.0382,
    }

    result = monitoring_result_from_row(row)

    assert config.fail_on_warn is True
    assert config.min_rows == 5000
    assert result.monitoring_status == "pass"
    assert result.targeted_users == 1390
