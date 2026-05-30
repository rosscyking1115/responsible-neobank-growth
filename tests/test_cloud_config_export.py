from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_generator.config import GeneratorConfig
from src.cloud.config import load_cloud_config
from src.cloud.export import export_cloud_dataset


def test_load_cloud_config_defaults_to_local_mode() -> None:
    config = load_cloud_config({})

    assert config.environment == "local"
    assert config.duckdb_path == Path("neobank.duckdb")
    assert config.cloud_export_dir == Path("data/cloud_export/demo")
    assert config.bigquery_raw_dataset == "neobank_raw"
    assert config.gcs_scoring_prefix == "neobank/scoring/activation"
    assert config.bigquery_max_bytes_billed == 1_000_000_000
    assert not config.require_gcp_confirmation


def test_load_cloud_config_validates_gcp_required_values() -> None:
    with pytest.raises(ValueError, match="GCP_PROJECT_ID"):
        load_cloud_config({"NEOBANK_ENV": "gcp"})


def test_load_cloud_config_accepts_gcp_mode_when_required_values_exist() -> None:
    config = load_cloud_config(
        {
            "NEOBANK_ENV": "gcp",
            "GCP_PROJECT_ID": "portfolio-project",
            "NEOBANK_GCS_RAW_BUCKET": "portfolio-raw",
            "NEOBANK_REQUIRE_GCP_CONFIRMATION": "true",
        }
    )

    assert config.is_gcp
    assert config.gcp_project_id == "portfolio-project"
    assert config.gcs_raw_bucket == "portfolio-raw"
    assert config.require_gcp_confirmation


def test_cloud_export_writes_parquet_files_and_manifest(tmp_path: Path) -> None:
    manifest = export_cloud_dataset(
        GeneratorConfig(users=150, months=2, seed=7),
        tmp_path,
        profile="demo",
    )

    manifest_path = tmp_path / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    table_names = {table["name"] for table in payload["tables"]}

    assert manifest["schema_version"]
    assert payload["format"] == "parquet"
    assert payload["generator_config"]["users"] == 150
    assert "users" in table_names
    assert "transactions" in table_names
    assert "pricing_exposures" in table_names
    assert len(payload["tables"]) == 13
    assert all((tmp_path / table["file"]).exists() for table in payload["tables"])
    assert all(table["row_count"] > 0 for table in payload["tables"])
    assert all(table["size_bytes"] > 0 for table in payload["tables"])
