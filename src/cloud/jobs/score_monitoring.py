"""Cloud Run Job entrypoint for BigQuery activation score monitoring."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import Any

from src.cloud.bigquery_score_monitoring_plan import (
    TABLE_NAME,
    build_score_monitoring_plan,
    render_score_monitoring_sql,
)

DEFAULT_BQ_LOCATION = "EU"
DEFAULT_BQ_ML_DATASET = "neobank_ml"
DEFAULT_BQ_MONITORING_DATASET = "neobank_monitoring"
MONITORING_TABLE = "score_monitoring_daily"


@dataclass(frozen=True)
class ScoreMonitoringJobConfig:
    score_date: date
    project: str
    bq_location: str
    score_dataset: str
    monitoring_dataset: str
    score_table: str
    min_rows: int
    max_vulnerable_review_rate: float
    fail_on_warn: bool


@dataclass(frozen=True)
class ScoreMonitoringJobResult:
    score_date: date
    monitoring_status: str
    scored_users: int
    unique_users: int
    targeted_users: int
    targeting_rate: float
    vulnerable_review_users: int
    vulnerable_review_rate: float


def _required_env(name: str, values: dict[str, str]) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise ValueError(f"Required environment variable is missing: {name}")
    return value


def _date_from_env(value: str | None) -> date:
    if value:
        return date.fromisoformat(value)
    return datetime.now(UTC).date()


def _bool_from_env(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "y"}


def load_score_monitoring_job_config(
    values: dict[str, str] | None = None,
) -> ScoreMonitoringJobConfig:
    env = values or os.environ
    return ScoreMonitoringJobConfig(
        score_date=_date_from_env(env.get("NEOBANK_SCORE_DATE")),
        project=_required_env("GCP_PROJECT_ID", env),
        bq_location=env.get("NEOBANK_BQ_LOCATION", DEFAULT_BQ_LOCATION),
        score_dataset=env.get("NEOBANK_BQ_ML_DATASET", DEFAULT_BQ_ML_DATASET),
        monitoring_dataset=env.get(
            "NEOBANK_BQ_MONITORING_DATASET",
            DEFAULT_BQ_MONITORING_DATASET,
        ),
        score_table=env.get("NEOBANK_BQ_SCORE_TABLE", TABLE_NAME),
        min_rows=int(env.get("NEOBANK_SCORE_MONITORING_MIN_ROWS", "100")),
        max_vulnerable_review_rate=float(
            env.get("NEOBANK_SCORE_MONITORING_MAX_VULNERABLE_REVIEW_RATE", "0.10")
        ),
        fail_on_warn=_bool_from_env(env.get("NEOBANK_SCORE_MONITORING_FAIL_ON_WARN")),
    )


def _ensure_monitoring_dataset(client, *, dataset_ref: str, location: str) -> None:
    from google.api_core.exceptions import NotFound
    from google.cloud import bigquery

    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location
        client.create_dataset(dataset)


def _ensure_monitoring_table(client, *, table_ref: str) -> None:
    from google.api_core.exceptions import NotFound
    from google.cloud import bigquery

    try:
        client.get_table(table_ref)
    except NotFound:
        schema = [
            bigquery.SchemaField("observed_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("score_date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("monitoring_status", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("scored_users", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("unique_users", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("targeted_users", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("targeting_rate", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("vulnerable_review_users", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("vulnerable_review_rate", "FLOAT", mode="REQUIRED"),
        ]
        table = bigquery.Table(table_ref, schema=schema)
        client.create_table(table)


def monitoring_result_from_row(row: Any) -> ScoreMonitoringJobResult:
    return ScoreMonitoringJobResult(
        score_date=row["score_date"],
        monitoring_status=str(row["monitoring_status"]),
        scored_users=int(row["scored_users"]),
        unique_users=int(row["unique_users"]),
        targeted_users=int(row["targeted_users"]),
        targeting_rate=float(row["targeting_rate"]),
        vulnerable_review_users=int(row["vulnerable_review_users"]),
        vulnerable_review_rate=float(row["vulnerable_review_rate"]),
    )


def write_monitoring_result(
    config: ScoreMonitoringJobConfig,
    result: ScoreMonitoringJobResult,
) -> None:
    from google.cloud import bigquery

    client = bigquery.Client(project=config.project, location=config.bq_location)
    dataset_ref = f"{config.project}.{config.monitoring_dataset}"
    table_ref = f"{dataset_ref}.{MONITORING_TABLE}"
    _ensure_monitoring_dataset(client, dataset_ref=dataset_ref, location=config.bq_location)
    _ensure_monitoring_table(client, table_ref=table_ref)
    payload = {
        "observed_at": datetime.now(UTC).isoformat(),
        **asdict(result),
        "score_date": result.score_date.isoformat(),
    }
    errors = client.insert_rows_json(table_ref, [payload])
    if errors:
        raise RuntimeError(f"Failed to insert score monitoring result: {errors}")


def run_score_monitoring_job(config: ScoreMonitoringJobConfig) -> ScoreMonitoringJobResult:
    from google.cloud import bigquery

    plan = build_score_monitoring_plan(
        score_date=config.score_date,
        project=config.project,
        dataset=config.score_dataset,
        location=config.bq_location,
        table=config.score_table,
        min_rows=config.min_rows,
        max_vulnerable_review_rate=config.max_vulnerable_review_rate,
    )
    client = bigquery.Client(project=config.project, location=config.bq_location)
    rows = list(client.query(render_score_monitoring_sql(plan)).result())
    if not rows:
        raise RuntimeError(f"No score rows found for {config.score_date.isoformat()}.")

    result = monitoring_result_from_row(rows[0])
    write_monitoring_result(config, result)
    if result.monitoring_status == "fail":
        raise RuntimeError(f"Score monitoring failed: {result}")
    if result.monitoring_status == "warn" and config.fail_on_warn:
        raise RuntimeError(f"Score monitoring warned and fail-on-warn is enabled: {result}")
    return result


def _json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def main() -> None:
    config = load_score_monitoring_job_config()
    result = run_score_monitoring_job(config)
    print(json.dumps(asdict(result), default=_json_default, sort_keys=True))


if __name__ == "__main__":
    main()
