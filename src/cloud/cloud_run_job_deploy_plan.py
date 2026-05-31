"""Render Cloud Run Job deployment commands for scoring and monitoring jobs."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

PROJECT_ENV_REF = "${GCP_PROJECT_ID}"
PROJECT_NUMBER_ENV_REF = "${GCP_PROJECT_NUMBER}"
REGION_ENV_REF = "${NEOBANK_CLOUD_RUN_REGION}"
BUCKET_ENV_REF = "${NEOBANK_GCS_RAW_BUCKET}"
BQ_LOCATION_ENV_REF = "${NEOBANK_BQ_LOCATION}"
BQ_ML_DATASET_ENV_REF = "${NEOBANK_BQ_ML_DATASET}"
BQ_MONITORING_DATASET_ENV_REF = "${NEOBANK_BQ_MONITORING_DATASET}"
DEFAULT_REPOSITORY = "neobank"
DEFAULT_IMAGE_NAME = "neobank-jobs"
DEFAULT_SERVICE_ACCOUNT_ID = "neobank-jobs"
DEFAULT_SCORING_PREFIX = "neobank/scoring/activation"


@dataclass(frozen=True)
class CloudRunJobDeployPlan:
    project: str
    project_number: str
    region: str
    repository: str
    image_name: str
    service_account_id: str
    bucket: str
    bq_location: str
    bq_ml_dataset: str
    bq_monitoring_dataset: str
    gcs_scoring_prefix: str
    score_date: str | None
    users: int
    months: int

    @property
    def image_uri(self) -> str:
        return (
            f"{self.region}-docker.pkg.dev/{self.project}/"
            f"{self.repository}/{self.image_name}:latest"
        )

    @property
    def service_account_email(self) -> str:
        return f"{self.service_account_id}@{self.project}.iam.gserviceaccount.com"


def build_cloud_run_job_deploy_plan(
    *,
    project: str = PROJECT_ENV_REF,
    project_number: str = PROJECT_NUMBER_ENV_REF,
    region: str = REGION_ENV_REF,
    repository: str = DEFAULT_REPOSITORY,
    image_name: str = DEFAULT_IMAGE_NAME,
    service_account_id: str = DEFAULT_SERVICE_ACCOUNT_ID,
    bucket: str = BUCKET_ENV_REF,
    bq_location: str = BQ_LOCATION_ENV_REF,
    bq_ml_dataset: str = BQ_ML_DATASET_ENV_REF,
    bq_monitoring_dataset: str = BQ_MONITORING_DATASET_ENV_REF,
    gcs_scoring_prefix: str = DEFAULT_SCORING_PREFIX,
    score_date: str | None = None,
    users: int = 5_000,
    months: int = 6,
) -> CloudRunJobDeployPlan:
    return CloudRunJobDeployPlan(
        project=project,
        project_number=project_number,
        region=region,
        repository=repository,
        image_name=image_name,
        service_account_id=service_account_id,
        bucket=bucket,
        bq_location=bq_location,
        bq_ml_dataset=bq_ml_dataset,
        bq_monitoring_dataset=bq_monitoring_dataset,
        gcs_scoring_prefix=gcs_scoring_prefix,
        score_date=score_date,
        users=users,
        months=months,
    )


def render_enable_services_command() -> str:
    return (
        "gcloud services enable "
        "artifactregistry.googleapis.com cloudbuild.googleapis.com "
        "run.googleapis.com cloudscheduler.googleapis.com"
    )


def render_artifact_repository_command(plan: CloudRunJobDeployPlan) -> str:
    return " ".join(
        [
            "gcloud artifacts repositories create",
            plan.repository,
            "--repository-format=docker",
            f"--location={plan.region}",
            '--description="Neobank Cloud Run job images"',
        ]
    )


def render_build_command(plan: CloudRunJobDeployPlan) -> str:
    return (
        "gcloud builds submit "
        "--config cloudbuild.jobs.yaml "
        f"--substitutions _IMAGE_URI={plan.image_uri} ."
    )


def render_service_account_command(plan: CloudRunJobDeployPlan) -> str:
    return " ".join(
        [
            "gcloud iam service-accounts create",
            plan.service_account_id,
            f"--project={plan.project}",
            '--display-name="Neobank batch jobs"',
        ]
    )


def render_project_iam_commands(plan: CloudRunJobDeployPlan) -> list[str]:
    member = f"serviceAccount:{plan.service_account_email}"
    return [
        " ".join(
            [
                "gcloud projects add-iam-policy-binding",
                plan.project,
                f"--member={member}",
                "--role=roles/bigquery.jobUser",
            ]
        ),
        " ".join(
            [
                "gcloud projects add-iam-policy-binding",
                plan.project,
                f"--member={member}",
                "--role=roles/bigquery.dataEditor",
            ]
        ),
        " ".join(
            [
                "gcloud storage buckets add-iam-policy-binding",
                f"gs://{plan.bucket}",
                f"--member={member}",
                "--role=roles/storage.objectAdmin",
            ]
        ),
    ]


def _env_vars(plan: CloudRunJobDeployPlan) -> str:
    env_vars = [
        f"GCP_PROJECT_ID={plan.project}",
        f"NEOBANK_BQ_LOCATION={plan.bq_location}",
        f"NEOBANK_BQ_ML_DATASET={plan.bq_ml_dataset}",
        f"NEOBANK_BQ_MONITORING_DATASET={plan.bq_monitoring_dataset}",
        f"NEOBANK_GCS_RAW_BUCKET={plan.bucket}",
        f"NEOBANK_GCS_SCORING_PREFIX={plan.gcs_scoring_prefix}",
        f"NEOBANK_JOB_USERS={plan.users}",
        f"NEOBANK_JOB_MONTHS={plan.months}",
        "NEOBANK_SCORE_MONITORING_MIN_ROWS=5000",
    ]
    if plan.score_date:
        env_vars.append(f"NEOBANK_SCORE_DATE={plan.score_date}")
    return ",".join(env_vars)


def render_scoring_job_create_command(plan: CloudRunJobDeployPlan) -> str:
    return " ".join(
        [
            "gcloud run jobs create neobank-activation-score-load",
            f"--image={plan.image_uri}",
            f"--region={plan.region}",
            f"--service-account={plan.service_account_email}",
            "--tasks=1",
            "--max-retries=1",
            "--task-timeout=3600",
            "--memory=2Gi",
            "--cpu=1",
            f"--set-env-vars={_env_vars(plan)}",
            "--command=python",
            "--args=-m,src.cloud.jobs.activation_score_load",
        ]
    )


def render_monitoring_job_create_command(plan: CloudRunJobDeployPlan) -> str:
    return " ".join(
        [
            "gcloud run jobs create neobank-score-monitoring",
            f"--image={plan.image_uri}",
            f"--region={plan.region}",
            f"--service-account={plan.service_account_email}",
            "--tasks=1",
            "--max-retries=1",
            "--task-timeout=900",
            "--memory=1Gi",
            "--cpu=1",
            f"--set-env-vars={_env_vars(plan)}",
            "--command=python",
            "--args=-m,src.cloud.jobs.score_monitoring",
        ]
    )


def render_job_execute_commands(plan: CloudRunJobDeployPlan) -> list[str]:
    return [
        f"gcloud run jobs execute neobank-activation-score-load --region={plan.region} --wait",
        f"gcloud run jobs execute neobank-score-monitoring --region={plan.region} --wait",
    ]


def render_cloud_run_job_deploy_plan(plan: CloudRunJobDeployPlan) -> str:
    setup_commands = [
        render_enable_services_command(),
        render_artifact_repository_command(plan),
        render_service_account_command(plan),
        *render_project_iam_commands(plan),
        render_build_command(plan),
        render_scoring_job_create_command(plan),
        render_monitoring_job_create_command(plan),
    ]
    return "\n".join(
        [
            "# Cloud Run Job Deployment Plan",
            "",
            f"Project: `{plan.project}`",
            f"Project number: `{plan.project_number}`",
            f"Region: `{plan.region}`",
            f"Image: `{plan.image_uri}`",
            f"Job service account: `{plan.service_account_email}`",
            f"Score date: `{plan.score_date or 'runtime UTC date'}`",
            "",
            "The jobs use `cloudbuild.jobs.yaml`, `Dockerfile.jobs`, and Python module",
            "entrypoints:",
            "",
            "- `src.cloud.jobs.activation_score_load`",
            "- `src.cloud.jobs.score_monitoring`",
            "",
            "Skip create commands for resources that already exist.",
            "",
            "## Create jobs",
            "",
            "```powershell",
            *setup_commands,
            "```",
            "",
            "## Smoke test jobs",
            "",
            "```powershell",
            *render_job_execute_commands(plan),
            "```",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Cloud Run Job deployment commands.")
    parser.add_argument("--project", default=PROJECT_ENV_REF)
    parser.add_argument("--project-number", default=PROJECT_NUMBER_ENV_REF)
    parser.add_argument("--region", default=REGION_ENV_REF)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--image-name", default=DEFAULT_IMAGE_NAME)
    parser.add_argument("--service-account-id", default=DEFAULT_SERVICE_ACCOUNT_ID)
    parser.add_argument("--bucket", default=BUCKET_ENV_REF)
    parser.add_argument("--bq-location", default=BQ_LOCATION_ENV_REF)
    parser.add_argument("--bq-ml-dataset", default=BQ_ML_DATASET_ENV_REF)
    parser.add_argument("--bq-monitoring-dataset", default=BQ_MONITORING_DATASET_ENV_REF)
    parser.add_argument("--gcs-scoring-prefix", default=DEFAULT_SCORING_PREFIX)
    parser.add_argument(
        "--score-date",
        default=None,
        help="Optional fixed score date for reproducible demo runs; omit for runtime UTC date.",
    )
    parser.add_argument("--users", type=int, default=5_000)
    parser.add_argument("--months", type=int, default=6)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = build_cloud_run_job_deploy_plan(
        project=args.project,
        project_number=args.project_number,
        region=args.region,
        repository=args.repository,
        image_name=args.image_name,
        service_account_id=args.service_account_id,
        bucket=args.bucket,
        bq_location=args.bq_location,
        bq_ml_dataset=args.bq_ml_dataset,
        bq_monitoring_dataset=args.bq_monitoring_dataset,
        gcs_scoring_prefix=args.gcs_scoring_prefix,
        score_date=args.score_date,
        users=args.users,
        months=args.months,
    )
    print(render_cloud_run_job_deploy_plan(plan))


if __name__ == "__main__":
    main()
