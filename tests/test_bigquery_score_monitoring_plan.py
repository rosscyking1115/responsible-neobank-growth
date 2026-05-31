from __future__ import annotations

from datetime import date

from src.cloud.bigquery_score_monitoring_plan import (
    build_score_monitoring_plan,
    render_bq_query_command,
    render_score_monitoring_plan,
    render_score_monitoring_sql,
)


def test_build_score_monitoring_plan_defaults_to_score_table() -> None:
    plan = build_score_monitoring_plan(score_date=date(2025, 6, 30))

    assert plan.table_ref == "${GCP_PROJECT_ID}.${NEOBANK_BQ_ML_DATASET}.customer_scores_daily"
    assert plan.location == "${NEOBANK_BQ_LOCATION}"
    assert plan.min_rows == 100


def test_render_score_monitoring_sql_checks_volume_probability_and_review_rate() -> None:
    plan = build_score_monitoring_plan(
        score_date=date(2025, 6, 30),
        project="neobank-growth-platform-ross",
        dataset="neobank_ml",
        min_rows=5_000,
        max_vulnerable_review_rate=0.08,
    )

    sql = render_score_monitoring_sql(plan)

    assert "FROM `neobank-growth-platform-ross.neobank_ml.customer_scores_daily`" in sql
    assert "WHERE DATE(score_date) = DATE '2025-06-30'" in sql
    assert "COUNT(DISTINCT user_id) AS unique_users" in sql
    assert "SAFE_DIVIDE(COUNTIF(decision = 'target'), COUNT(*)) AS targeting_rate" in sql
    assert "APPROX_QUANTILES(activation_probability, 100)[OFFSET(50)]" in sql
    assert "WHEN scored_users < 5000 THEN 'fail'" in sql
    assert "WHEN vulnerable_review_rate > 0.080000 THEN 'warn'" in sql


def test_render_bq_query_command_is_powershell_safe_and_location_scoped() -> None:
    plan = build_score_monitoring_plan(
        score_date=date(2025, 6, 30),
        project="neobank-growth-platform-ross",
        dataset="neobank_ml",
        location="EU",
    )

    command = render_bq_query_command(plan)

    assert command.startswith("bq --location=EU query --use_legacy_sql=false '")
    assert "DATE ''2025-06-30''" in command
    assert "decision = ''target''" in command


def test_render_score_monitoring_plan_includes_operational_context() -> None:
    plan = build_score_monitoring_plan(
        score_date=date(2025, 6, 30),
        project="neobank-growth-platform-ross",
        dataset="neobank_ml",
        location="EU",
        min_rows=5_000,
    )

    rendered = render_score_monitoring_plan(plan)

    assert "BigQuery Activation Score Monitoring Plan" in rendered
    assert "Score date: 2025-06-30" in rendered
    assert (
        "BigQuery table: `neobank-growth-platform-ross.neobank_ml.customer_scores_daily`"
        in rendered
    )
    assert "Minimum scored users: 5,000" in rendered
    assert "bq --location=EU query" in rendered
