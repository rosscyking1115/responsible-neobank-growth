"""Render BigQuery load commands for activation batch-score extracts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SCORE_FILE_NAME = "customer_scores_daily.parquet"
DEFAULT_SCORE_DIR = Path("artifacts/scoring/activation")
PROJECT_ENV_REF = "${GCP_PROJECT_ID}"
LOCATION_ENV_REF = "${NEOBANK_BQ_LOCATION}"
DATASET_ENV_REF = "${NEOBANK_BQ_ML_DATASET}"
BUCKET_ENV_REF = "${NEOBANK_GCS_RAW_BUCKET}"
PREFIX_ENV_REF = "${NEOBANK_GCS_SCORING_PREFIX}"


@dataclass(frozen=True)
class ScoreLoadPlan:
    score_date: date
    local_score_path: Path
    destination_uri: str
    table_ref: str
    location: str


def score_partition_path(score_dir: Path, score_date: date) -> Path:
    return score_dir / f"score_date={score_date.isoformat()}" / SCORE_FILE_NAME


def destination_uri(
    *,
    bucket: str,
    prefix: str,
    score_date: date,
    file_name: str = SCORE_FILE_NAME,
) -> str:
    cleaned_prefix = prefix.strip("/")
    return f"gs://{bucket}/{cleaned_prefix}/score_date={score_date.isoformat()}/{file_name}"


def table_ref(project: str, dataset: str, table: str = "customer_scores_daily") -> str:
    return f"{project}:{dataset}.{table}"


def build_score_load_plan(
    *,
    score_date: date,
    score_dir: Path = DEFAULT_SCORE_DIR,
    project: str = PROJECT_ENV_REF,
    dataset: str = DATASET_ENV_REF,
    location: str = LOCATION_ENV_REF,
    bucket: str = BUCKET_ENV_REF,
    prefix: str = PREFIX_ENV_REF,
) -> ScoreLoadPlan:
    return ScoreLoadPlan(
        score_date=score_date,
        local_score_path=score_partition_path(score_dir, score_date),
        destination_uri=destination_uri(bucket=bucket, prefix=prefix, score_date=score_date),
        table_ref=table_ref(project, dataset),
        location=location,
    )


def render_upload_command(plan: ScoreLoadPlan) -> str:
    return f"gcloud storage cp {plan.local_score_path.as_posix()} {plan.destination_uri}"


def render_dataset_command(
    *,
    project: str = PROJECT_ENV_REF,
    dataset: str = DATASET_ENV_REF,
    location: str = LOCATION_ENV_REF,
) -> str:
    return f"bq --location={location} mk --dataset --if_not_exists {project}:{dataset}"


def render_plan_dataset_command(plan: ScoreLoadPlan, *, location: str = LOCATION_ENV_REF) -> str:
    dataset_ref = plan.table_ref.rsplit(".", 1)[0]
    return f"bq --location={location} mk --dataset --if_not_exists {dataset_ref}"


def render_load_command(plan: ScoreLoadPlan, *, location: str = LOCATION_ENV_REF) -> str:
    return " ".join(
        [
            "bq",
            f"--location={location}",
            "load",
            "--source_format=PARQUET",
            "--replace",
            "--time_partitioning_field=score_date",
            "--clustering_fields=model_version,decision,region",
            plan.table_ref,
            plan.destination_uri,
        ]
    )


def render_verification_command(plan: ScoreLoadPlan) -> str:
    sql = (
        "SELECT "
        "score_date, "
        "COUNT(*) AS scored_users, "
        "COUNTIF(decision = 'target') AS targeted_users, "
        "COUNTIF(vulnerable_customer_review) AS vulnerable_review_users "
        f"FROM `{plan.table_ref.replace(':', '.')}` "
        f"WHERE score_date = DATE '{plan.score_date.isoformat()}' "
        "GROUP BY score_date"
    )
    powershell_sql = sql.replace("'", "''")
    return f"bq query --use_legacy_sql=false '{powershell_sql}'"


def validate_score_file(plan: ScoreLoadPlan) -> None:
    if not plan.local_score_path.exists():
        raise FileNotFoundError(
            "Score extract does not exist. Generate it first with "
            "`uv run python -m src.modelling.batch_score_activation "
            f"--score-date {plan.score_date.isoformat()}`."
        )


def render_score_load_plan(plan: ScoreLoadPlan) -> str:
    return "\n".join(
        [
            "# BigQuery Activation Score Load Plan",
            "",
            f"Score date: {plan.score_date.isoformat()}",
            f"Local score extract: `{plan.local_score_path.as_posix()}`",
            f"Cloud Storage destination: `{plan.destination_uri}`",
            f"BigQuery table: `{plan.table_ref}`",
            "",
            "Set these environment variables before running the commands:",
            "",
            "- `GCP_PROJECT_ID`",
            "- `NEOBANK_BQ_LOCATION`",
            "- `NEOBANK_BQ_ML_DATASET`",
            "- `NEOBANK_GCS_RAW_BUCKET`",
            "- `NEOBANK_GCS_SCORING_PREFIX`",
            "",
            "```powershell",
            render_upload_command(plan),
            render_plan_dataset_command(plan, location=plan.location),
            render_load_command(plan, location=plan.location),
            render_verification_command(plan),
            "```",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render BigQuery activation score load commands.")
    parser.add_argument("--score-date", type=date.fromisoformat, required=True)
    parser.add_argument("--score-dir", type=Path, default=DEFAULT_SCORE_DIR)
    parser.add_argument("--project", default=PROJECT_ENV_REF)
    parser.add_argument("--dataset", default=DATASET_ENV_REF)
    parser.add_argument("--location", default=LOCATION_ENV_REF)
    parser.add_argument("--bucket", default=BUCKET_ENV_REF)
    parser.add_argument("--prefix", default=PREFIX_ENV_REF)
    parser.add_argument(
        "--skip-file-check",
        action="store_true",
        help="Render commands without checking that the local score parquet exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = build_score_load_plan(
        score_date=args.score_date,
        score_dir=args.score_dir,
        project=args.project,
        dataset=args.dataset,
        location=args.location,
        bucket=args.bucket,
        prefix=args.prefix,
    )
    if not args.skip_file_check:
        validate_score_file(plan)
    print(render_score_load_plan(plan))


if __name__ == "__main__":
    main()
