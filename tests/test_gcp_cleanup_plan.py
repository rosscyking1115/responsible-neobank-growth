from __future__ import annotations

from pathlib import Path

from src.cloud.gcp_cleanup_plan import (
    GcpCleanupConfig,
    render_apply_lifecycle_command,
    render_cleanup_plan,
    render_delete_bq_dataset_command,
    render_gcs_prefix_uri,
    render_remove_gcs_prefix_command,
)


def test_render_gcs_prefix_uri_strips_extra_slashes() -> None:
    assert (
        render_gcs_prefix_uri("neobank-growth-platform-ross-raw", "/neobank/raw/demo/")
        == "gs://neobank-growth-platform-ross-raw/neobank/raw/demo"
    )


def test_apply_lifecycle_command_uses_bucket_update_and_lifecycle_file() -> None:
    config = GcpCleanupConfig(
        bucket="neobank-growth-platform-ross-raw",
        lifecycle_file=Path("cloud/gcp/gcs_lifecycle_demo.json"),
    )

    command = render_apply_lifecycle_command(config)

    assert command == (
        "gcloud storage buckets update gs://neobank-growth-platform-ross-raw "
        "--lifecycle-file=cloud/gcp/gcs_lifecycle_demo.json"
    )


def test_destructive_commands_are_explicit_and_scoped() -> None:
    config = GcpCleanupConfig(
        project="neobank-growth-platform-ross",
        dataset="neobank_raw",
        bucket="neobank-growth-platform-ross-raw",
        prefix="neobank/raw/demo",
    )

    assert render_remove_gcs_prefix_command(config) == (
        "gcloud storage rm --recursive "
        "gs://neobank-growth-platform-ross-raw/neobank/raw/demo/**"
    )
    assert (
        render_delete_bq_dataset_command(config)
        == "bq rm -r -f neobank-growth-platform-ross:neobank_raw"
    )


def test_cleanup_plan_separates_inventory_from_destructive_cleanup() -> None:
    config = GcpCleanupConfig(
        project="neobank-growth-platform-ross",
        dataset="neobank_raw",
        bucket="neobank-growth-platform-ross-raw",
        prefix="neobank/raw/demo",
    )

    plan = render_cleanup_plan(config)

    assert "Pre-cleanup inventory checks" in plan
    assert "Destructive cleanup commands" in plan
    assert "bq ls neobank-growth-platform-ross:neobank_raw" in plan
    assert "gcloud storage rm --recursive" in plan
