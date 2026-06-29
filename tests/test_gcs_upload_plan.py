from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_generator.config import GeneratorConfig
from src.cloud.export import export_cloud_dataset
from src.cloud.gcs_upload_plan import (
    load_export_manifest,
    render_gcs_upload_command,
    render_upload_plan,
    validate_export_files,
)


def test_load_export_manifest_reads_cloud_export(tmp_path: Path) -> None:
    export_cloud_dataset(GeneratorConfig(users=120, months=1, seed=11), tmp_path, "demo")

    manifest = load_export_manifest(tmp_path / "manifest.json")

    assert manifest.manifest_version == 1
    assert manifest.schema_version
    assert manifest.profile == "demo"
    assert manifest.source_format == "parquet"
    assert len(manifest.tables) == 16
    assert {table.file for table in manifest.tables} >= {"users.parquet", "transactions.parquet"}


def test_render_gcs_upload_command_uses_file_and_destination_prefix(tmp_path: Path) -> None:
    export_cloud_dataset(GeneratorConfig(users=120, months=1, seed=11), tmp_path, "demo")
    manifest = load_export_manifest(tmp_path / "manifest.json")
    users = next(table for table in manifest.tables if table.name == "users")

    command = render_gcs_upload_command(
        users,
        tmp_path,
        bucket="portfolio-raw",
        prefix="neobank/raw/demo",
    )

    assert command.startswith("gcloud storage cp ")
    assert command.endswith("gs://portfolio-raw/neobank/raw/demo/users.parquet")
    assert "users.parquet" in command


def test_render_upload_plan_summarises_export_and_lists_commands(tmp_path: Path) -> None:
    export_cloud_dataset(GeneratorConfig(users=120, months=1, seed=11), tmp_path, "demo")
    manifest = load_export_manifest(tmp_path / "manifest.json")

    plan = render_upload_plan(manifest, tmp_path)

    assert "Cloud Storage Raw Upload Plan" in plan
    assert "Tables: 16" in plan
    assert "`NEOBANK_GCS_RAW_BUCKET`" in plan
    assert "gcloud storage cp" in plan
    assert "gs://${NEOBANK_GCS_RAW_BUCKET}/${NEOBANK_GCS_RAW_PREFIX}/users.parquet" in plan


def test_validate_export_files_rejects_missing_parquet(tmp_path: Path) -> None:
    export_cloud_dataset(GeneratorConfig(users=120, months=1, seed=11), tmp_path, "demo")
    manifest = load_export_manifest(tmp_path / "manifest.json")
    (tmp_path / "users.parquet").unlink()

    with pytest.raises(FileNotFoundError, match="users.parquet"):
        validate_export_files(manifest, tmp_path)


def test_load_export_manifest_rejects_duplicate_files(tmp_path: Path) -> None:
    export_cloud_dataset(GeneratorConfig(users=120, months=1, seed=11), tmp_path, "demo")
    manifest_path = tmp_path / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["tables"][1]["file"] = payload["tables"][0]["file"]
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unique"):
        load_export_manifest(manifest_path)
