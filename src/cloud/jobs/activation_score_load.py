"""Cloud Run Job entrypoint for activation scoring and BigQuery loading."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol

from src.cloud.bigquery_score_load_plan import (
    SCORE_FILE_NAME,
    destination_uri,
    score_partition_path,
)
from src.modelling.artifacts import REGISTRY_FILENAME

DEFAULT_JOB_WORKDIR = Path("/tmp/neobank-activation-score-load")
DEFAULT_BQ_LOCATION = "EU"
DEFAULT_BQ_ML_DATASET = "neobank_ml"
DEFAULT_GCS_SCORING_PREFIX = "neobank/scoring/activation"
DEFAULT_USERS = 5_000
DEFAULT_MONTHS = 6
SCORE_TABLE = "customer_scores_daily"
CLUSTERING_FIELDS = ["model_version", "decision", "region"]


class CommandRunner(Protocol):
    def __call__(self, args: list[str], *, env: dict[str, str] | None = None) -> None: ...


@dataclass(frozen=True)
class ActivationScoreLoadJobConfig:
    score_date: date
    project: str
    bq_location: str
    bq_dataset: str
    gcs_bucket: str
    gcs_prefix: str
    working_dir: Path
    users: int
    months: int

    @property
    def raw_path(self) -> Path:
        return self.working_dir / "raw"

    @property
    def duckdb_path(self) -> Path:
        return self.working_dir / "neobank.duckdb"

    @property
    def model_card_path(self) -> Path:
        return self.working_dir / "model_card" / "MODEL_ACTIVATION_DECISIONING.md"

    @property
    def artifact_dir(self) -> Path:
        return self.working_dir / "artifacts" / "models" / "activation"

    @property
    def registry_path(self) -> Path:
        return self.artifact_dir / REGISTRY_FILENAME

    @property
    def score_dir(self) -> Path:
        return self.working_dir / "artifacts" / "scoring" / "activation"

    @property
    def score_path(self) -> Path:
        return score_partition_path(self.score_dir, self.score_date)

    @property
    def gcs_uri(self) -> str:
        return destination_uri(
            bucket=self.gcs_bucket,
            prefix=self.gcs_prefix,
            score_date=self.score_date,
            file_name=SCORE_FILE_NAME,
        )


@dataclass(frozen=True)
class ActivationScoreLoadJobResult:
    score_date: date
    local_score_path: Path
    gcs_uri: str
    bq_table: str
    rows_loaded: int | None


def _required_env(name: str, values: dict[str, str]) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise ValueError(f"Required environment variable is missing: {name}")
    return value


def _date_from_env(value: str | None) -> date:
    if value:
        return date.fromisoformat(value)
    return datetime.now(UTC).date()


def _int_from_env(values: dict[str, str], name: str, default: int) -> int:
    value = values.get(name)
    return int(value) if value else default


def load_activation_score_load_job_config(
    values: dict[str, str] | None = None,
) -> ActivationScoreLoadJobConfig:
    env = values or os.environ
    return ActivationScoreLoadJobConfig(
        score_date=_date_from_env(env.get("NEOBANK_SCORE_DATE")),
        project=_required_env("GCP_PROJECT_ID", env),
        bq_location=env.get("NEOBANK_BQ_LOCATION", DEFAULT_BQ_LOCATION),
        bq_dataset=env.get("NEOBANK_BQ_ML_DATASET", DEFAULT_BQ_ML_DATASET),
        gcs_bucket=_required_env("NEOBANK_GCS_RAW_BUCKET", env),
        gcs_prefix=env.get("NEOBANK_GCS_SCORING_PREFIX", DEFAULT_GCS_SCORING_PREFIX),
        working_dir=Path(env.get("NEOBANK_JOB_WORKDIR", str(DEFAULT_JOB_WORKDIR))),
        users=_int_from_env(env, "NEOBANK_JOB_USERS", DEFAULT_USERS),
        months=_int_from_env(env, "NEOBANK_JOB_MONTHS", DEFAULT_MONTHS),
    )


def run_command(args: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, check=True, env=env)


def prepare_working_directory(config: ActivationScoreLoadJobConfig) -> None:
    config.working_dir.mkdir(parents=True, exist_ok=True)
    if config.duckdb_path.exists():
        config.duckdb_path.unlink()


def run_local_scoring_pipeline(
    config: ActivationScoreLoadJobConfig,
    *,
    runner: CommandRunner = run_command,
) -> None:
    prepare_working_directory(config)
    runner(
        [
            sys.executable,
            "-m",
            "data_generator.generate",
            "--users",
            str(config.users),
            "--months",
            str(config.months),
            "--output-dir",
            config.raw_path.as_posix(),
        ]
    )
    dbt_env = os.environ.copy()
    dbt_env["NEOBANK_DUCKDB_PATH"] = config.duckdb_path.as_posix()
    runner(
        [
            "dbt",
            "build",
            "--project-dir",
            "dbt_neobank",
            "--profiles-dir",
            "dbt_neobank",
            "--vars",
            f"{{raw_path: {config.raw_path.as_posix()}}}",
        ],
        env=dbt_env,
    )
    runner(
        [
            sys.executable,
            "-m",
            "src.modelling.run_activation_model",
            "--db",
            config.duckdb_path.as_posix(),
            "--output",
            config.model_card_path.as_posix(),
            "--artifact-dir",
            config.artifact_dir.as_posix(),
        ]
    )
    runner(
        [
            sys.executable,
            "-m",
            "src.modelling.batch_score_activation",
            "--db",
            config.duckdb_path.as_posix(),
            "--registry",
            config.registry_path.as_posix(),
            "--output-dir",
            config.score_dir.as_posix(),
            "--score-date",
            config.score_date.isoformat(),
        ]
    )


def upload_score_extract_to_gcs(config: ActivationScoreLoadJobConfig) -> None:
    from google.cloud import storage

    blob_name = (
        f"{config.gcs_prefix.strip('/')}/score_date={config.score_date.isoformat()}/"
        f"{SCORE_FILE_NAME}"
    )
    client = storage.Client(project=config.project)
    bucket = client.bucket(config.gcs_bucket)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(config.score_path.as_posix())


def _ensure_bigquery_dataset(client, *, dataset_ref: str, location: str) -> None:
    from google.api_core.exceptions import NotFound
    from google.cloud import bigquery

    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location
        client.create_dataset(dataset)


def load_score_extract_to_bigquery(config: ActivationScoreLoadJobConfig) -> int | None:
    from google.api_core.exceptions import NotFound
    from google.cloud import bigquery

    client = bigquery.Client(project=config.project, location=config.bq_location)
    dataset_ref = f"{config.project}.{config.bq_dataset}"
    table_ref = f"{dataset_ref}.{SCORE_TABLE}"
    partition_ref = f"{table_ref}${config.score_date:%Y%m%d}"
    _ensure_bigquery_dataset(client, dataset_ref=dataset_ref, location=config.bq_location)

    try:
        client.get_table(table_ref)
        destination = partition_ref
        write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
    except NotFound:
        destination = table_ref
        write_disposition = bigquery.WriteDisposition.WRITE_APPEND

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=write_disposition,
        time_partitioning=bigquery.TimePartitioning(field="score_date"),
        clustering_fields=CLUSTERING_FIELDS,
    )
    load_job = client.load_table_from_uri(config.gcs_uri, destination, job_config=job_config)
    result = load_job.result()
    return getattr(result, "output_rows", None)


def run_activation_score_load_job(
    config: ActivationScoreLoadJobConfig,
    *,
    runner: CommandRunner = run_command,
) -> ActivationScoreLoadJobResult:
    run_local_scoring_pipeline(config, runner=runner)
    upload_score_extract_to_gcs(config)
    rows_loaded = load_score_extract_to_bigquery(config)
    return ActivationScoreLoadJobResult(
        score_date=config.score_date,
        local_score_path=config.score_path,
        gcs_uri=config.gcs_uri,
        bq_table=f"{config.project}.{config.bq_dataset}.{SCORE_TABLE}",
        rows_loaded=rows_loaded,
    )


def _json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return value.as_posix()
    return str(value)


def main() -> None:
    config = load_activation_score_load_job_config()
    result = run_activation_score_load_job(config)
    print(json.dumps(asdict(result), default=_json_default, sort_keys=True))


if __name__ == "__main__":
    main()
