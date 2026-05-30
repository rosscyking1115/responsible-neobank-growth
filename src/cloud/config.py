"""Environment-backed configuration for local and GCP execution modes."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

VALID_ENVIRONMENTS = {"local", "gcp"}


@dataclass(frozen=True)
class CloudConfig:
    environment: str
    duckdb_path: Path
    cloud_export_dir: Path
    gcp_project_id: str | None
    gcp_location: str
    google_application_credentials: Path | None
    bigquery_location: str
    bigquery_raw_dataset: str
    bigquery_mart_dataset: str
    bigquery_ml_dataset: str
    bigquery_monitoring_dataset: str
    gcs_raw_bucket: str | None
    gcs_raw_prefix: str
    bigquery_max_bytes_billed: int
    require_gcp_confirmation: bool

    @property
    def is_gcp(self) -> bool:
        return self.environment == "gcp"

    def validate_for_gcp(self) -> None:
        missing = []
        if not self.gcp_project_id:
            missing.append("GCP_PROJECT_ID")
        if not self.gcs_raw_bucket:
            missing.append("NEOBANK_GCS_RAW_BUCKET")
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"GCP mode requires these environment variables: {joined}.")


def _optional_string(env: Mapping[str, str], name: str) -> str | None:
    value = env.get(name, "").strip()
    return value or None


def _path(env: Mapping[str, str], name: str, default: str) -> Path:
    return Path(env.get(name, default)).expanduser()


def _optional_path(env: Mapping[str, str], name: str) -> Path | None:
    value = _optional_string(env, name)
    return Path(value).expanduser() if value else None


def _bool(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    value = env.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    value = env.get(name)
    if value is None or not value.strip():
        return default
    return int(value)


def load_cloud_config(env: Mapping[str, str] | None = None) -> CloudConfig:
    values = os.environ if env is None else env
    environment = values.get("NEOBANK_ENV", "local").strip().lower()
    if environment not in VALID_ENVIRONMENTS:
        valid = ", ".join(sorted(VALID_ENVIRONMENTS))
        raise ValueError(f"NEOBANK_ENV must be one of: {valid}.")

    config = CloudConfig(
        environment=environment,
        duckdb_path=_path(values, "NEOBANK_DUCKDB_PATH", "neobank.duckdb"),
        cloud_export_dir=_path(values, "NEOBANK_CLOUD_EXPORT_DIR", "data/cloud_export/demo"),
        gcp_project_id=_optional_string(values, "GCP_PROJECT_ID"),
        gcp_location=values.get("GCP_LOCATION", "europe-west2"),
        google_application_credentials=_optional_path(values, "GOOGLE_APPLICATION_CREDENTIALS"),
        bigquery_location=values.get("NEOBANK_BQ_LOCATION", "EU"),
        bigquery_raw_dataset=values.get("NEOBANK_BQ_RAW_DATASET", "neobank_raw"),
        bigquery_mart_dataset=values.get("NEOBANK_BQ_MART_DATASET", "neobank_mart"),
        bigquery_ml_dataset=values.get("NEOBANK_BQ_ML_DATASET", "neobank_ml"),
        bigquery_monitoring_dataset=values.get(
            "NEOBANK_BQ_MONITORING_DATASET", "neobank_monitoring"
        ),
        gcs_raw_bucket=_optional_string(values, "NEOBANK_GCS_RAW_BUCKET"),
        gcs_raw_prefix=values.get("NEOBANK_GCS_RAW_PREFIX", "neobank/raw/demo").strip("/"),
        bigquery_max_bytes_billed=_int(values, "NEOBANK_BQ_MAX_BYTES_BILLED", 1_000_000_000),
        require_gcp_confirmation=_bool(values, "NEOBANK_REQUIRE_GCP_CONFIRMATION"),
    )
    if config.is_gcp:
        config.validate_for_gcp()
    return config
