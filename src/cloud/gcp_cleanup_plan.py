"""Render GCP cleanup and cost-control commands for demo warehouse resources."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PROJECT = "${GCP_PROJECT_ID}"
DEFAULT_DATASET = "${NEOBANK_BQ_RAW_DATASET}"
DEFAULT_BUCKET = "${NEOBANK_GCS_RAW_BUCKET}"
DEFAULT_PREFIX = "${NEOBANK_GCS_RAW_PREFIX}"
DEFAULT_LIFECYCLE_FILE = Path("cloud/gcp/gcs_lifecycle_demo.json")


@dataclass(frozen=True)
class GcpCleanupConfig:
    project: str = DEFAULT_PROJECT
    dataset: str = DEFAULT_DATASET
    bucket: str = DEFAULT_BUCKET
    prefix: str = DEFAULT_PREFIX
    lifecycle_file: Path = DEFAULT_LIFECYCLE_FILE


def render_gcs_prefix_uri(bucket: str, prefix: str) -> str:
    cleaned_prefix = prefix.strip("/")
    return f"gs://{bucket}/{cleaned_prefix}"


def render_apply_lifecycle_command(config: GcpCleanupConfig) -> str:
    lifecycle_file = config.lifecycle_file.as_posix()
    return (
        f"gcloud storage buckets update gs://{config.bucket} "
        f"--lifecycle-file={lifecycle_file}"
    )


def render_list_gcs_prefix_command(config: GcpCleanupConfig) -> str:
    return f"gcloud storage ls {render_gcs_prefix_uri(config.bucket, config.prefix)}/**"


def render_remove_gcs_prefix_command(config: GcpCleanupConfig) -> str:
    return (
        "gcloud storage rm --recursive "
        f"{render_gcs_prefix_uri(config.bucket, config.prefix)}/**"
    )


def render_list_bq_tables_command(config: GcpCleanupConfig) -> str:
    return f"bq ls {config.project}:{config.dataset}"


def render_delete_bq_dataset_command(config: GcpCleanupConfig) -> str:
    return f"bq rm -r -f {config.project}:{config.dataset}"


def render_cleanup_plan(config: GcpCleanupConfig) -> str:
    lines = [
        "# GCP Demo Cleanup and Cost-Control Plan",
        "",
        "This plan renders commands only. Review before running anything destructive.",
        "",
        "Resources:",
        "",
        f"- Project: `{config.project}`",
        f"- BigQuery dataset: `{config.dataset}`",
        f"- Cloud Storage prefix: `{render_gcs_prefix_uri(config.bucket, config.prefix)}/`",
        f"- Lifecycle file: `{config.lifecycle_file.as_posix()}`",
        "",
        "Recommended cost-control setup:",
        "",
        "```powershell",
        render_apply_lifecycle_command(config),
        "```",
        "",
        "Pre-cleanup inventory checks:",
        "",
        "```powershell",
        render_list_bq_tables_command(config),
        render_list_gcs_prefix_command(config),
        "```",
        "",
        "Destructive cleanup commands, for when the demo cloud slice is no longer needed:",
        "",
        "```powershell",
        render_remove_gcs_prefix_command(config),
        render_delete_bq_dataset_command(config),
        "```",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render GCP cleanup and cost-control commands."
    )
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--lifecycle-file", type=Path, default=DEFAULT_LIFECYCLE_FILE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = GcpCleanupConfig(
        project=args.project,
        dataset=args.dataset,
        bucket=args.bucket,
        prefix=args.prefix,
        lifecycle_file=args.lifecycle_file,
    )
    print(render_cleanup_plan(config))


if __name__ == "__main__":
    main()
