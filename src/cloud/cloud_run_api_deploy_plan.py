"""Render Cloud Run service deployment commands for the prediction API."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

PROJECT_ENV_REF = "${GCP_PROJECT_ID}"
PROJECT_NUMBER_ENV_REF = "${GCP_PROJECT_NUMBER}"
REGION_ENV_REF = "${NEOBANK_CLOUD_RUN_REGION}"
INVOKER_ENV_REF = "${NEOBANK_API_INVOKER_EMAIL}"
DEFAULT_REPOSITORY = "neobank"
DEFAULT_IMAGE_NAME = "neobank-api"
DEFAULT_SERVICE_NAME = "neobank-api"
DEFAULT_SERVICE_ACCOUNT_ID = "neobank-api"
DEFAULT_DATA_VERSION = "synthetic-portfolio"


@dataclass(frozen=True)
class CloudRunApiDeployPlan:
    project: str
    project_number: str
    region: str
    repository: str
    image_name: str
    service_name: str
    service_account_id: str
    invoker_email: str
    data_version: str
    max_instances: int

    @property
    def image_uri(self) -> str:
        return (
            f"{self.region}-docker.pkg.dev/{self.project}/"
            f"{self.repository}/{self.image_name}:latest"
        )

    @property
    def service_account_email(self) -> str:
        return f"{self.service_account_id}@{self.project}.iam.gserviceaccount.com"


def build_cloud_run_api_deploy_plan(
    *,
    project: str = PROJECT_ENV_REF,
    project_number: str = PROJECT_NUMBER_ENV_REF,
    region: str = REGION_ENV_REF,
    repository: str = DEFAULT_REPOSITORY,
    image_name: str = DEFAULT_IMAGE_NAME,
    service_name: str = DEFAULT_SERVICE_NAME,
    service_account_id: str = DEFAULT_SERVICE_ACCOUNT_ID,
    invoker_email: str = INVOKER_ENV_REF,
    data_version: str = DEFAULT_DATA_VERSION,
    max_instances: int = 2,
) -> CloudRunApiDeployPlan:
    return CloudRunApiDeployPlan(
        project=project,
        project_number=project_number,
        region=region,
        repository=repository,
        image_name=image_name,
        service_name=service_name,
        service_account_id=service_account_id,
        invoker_email=invoker_email,
        data_version=data_version,
        max_instances=max_instances,
    )


def render_enable_services_command() -> str:
    return (
        "gcloud services enable "
        "artifactregistry.googleapis.com cloudbuild.googleapis.com run.googleapis.com"
    )


def render_artifact_repository_command(plan: CloudRunApiDeployPlan) -> str:
    return " ".join(
        [
            "gcloud artifacts repositories create",
            plan.repository,
            "--repository-format=docker",
            f"--location={plan.region}",
            '--description="Neobank Cloud Run service images"',
        ]
    )


def render_service_account_command(plan: CloudRunApiDeployPlan) -> str:
    return " ".join(
        [
            "gcloud iam service-accounts create",
            plan.service_account_id,
            f"--project={plan.project}",
            '--display-name="Neobank API service"',
        ]
    )


def render_build_command(plan: CloudRunApiDeployPlan) -> str:
    return (
        "gcloud builds submit "
        "--config cloudbuild.api.yaml "
        f"--substitutions _IMAGE_URI={plan.image_uri} ."
    )


def _env_vars(plan: CloudRunApiDeployPlan) -> str:
    return f"'^@^DATA_VERSION={plan.data_version}@NEOBANK_ENV=gcp'"


def render_service_deploy_command(plan: CloudRunApiDeployPlan) -> str:
    return " ".join(
        [
            "gcloud run deploy",
            plan.service_name,
            f"--image={plan.image_uri}",
            f"--region={plan.region}",
            "--platform=managed",
            f"--service-account={plan.service_account_email}",
            "--port=8080",
            "--memory=1Gi",
            "--cpu=1",
            "--min-instances=0",
            f"--max-instances={plan.max_instances}",
            "--timeout=300",
            "--concurrency=40",
            "--ingress=all",
            "--no-allow-unauthenticated",
            f"--set-env-vars={_env_vars(plan)}",
        ]
    )


def render_invoker_binding_command(plan: CloudRunApiDeployPlan) -> str:
    return " ".join(
        [
            "gcloud run services add-iam-policy-binding",
            plan.service_name,
            f"--region={plan.region}",
            f"--member=user:{plan.invoker_email}",
            "--role=roles/run.invoker",
        ]
    )


def render_service_url_command(plan: CloudRunApiDeployPlan) -> str:
    return (
        "$SERVICE_URL = gcloud run services describe "
        f"{plan.service_name} --region={plan.region} --format=\"value(status.url)\""
    )


def render_authenticated_health_check_commands(plan: CloudRunApiDeployPlan) -> list[str]:
    return [
        render_service_url_command(plan),
        "$TOKEN = gcloud auth print-identity-token",
        'Invoke-RestMethod -Headers @{Authorization="Bearer $TOKEN"} "$SERVICE_URL/health"',
    ]


def render_cloud_run_api_deploy_plan(plan: CloudRunApiDeployPlan) -> str:
    setup_commands = [
        render_enable_services_command(),
        render_artifact_repository_command(plan),
        render_service_account_command(plan),
        render_build_command(plan),
        render_service_deploy_command(plan),
        render_invoker_binding_command(plan),
    ]
    return "\n".join(
        [
            "# Cloud Run API Deployment Plan",
            "",
            f"Project: `{plan.project}`",
            f"Project number: `{plan.project_number}`",
            f"Region: `{plan.region}`",
            f"Image: `{plan.image_uri}`",
            f"Service: `{plan.service_name}`",
            f"Runtime service account: `{plan.service_account_email}`",
            f"Invoker email: `{plan.invoker_email}`",
            "",
            "This plan deploys the FastAPI prediction and pricing scenario service",
            "as a private Cloud Run service. It uses `cloudbuild.api.yaml` so Cloud",
            "Build uses `Dockerfile.api` rather than a default Dockerfile.",
            "Skip create commands for resources that already exist.",
            "",
            "## Deploy API",
            "",
            "```powershell",
            *setup_commands,
            "```",
            "",
            "## Authenticated Smoke Test",
            "",
            "```powershell",
            *render_authenticated_health_check_commands(plan),
            "```",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Cloud Run API deployment commands.")
    parser.add_argument("--project", default=PROJECT_ENV_REF)
    parser.add_argument("--project-number", default=PROJECT_NUMBER_ENV_REF)
    parser.add_argument("--region", default=REGION_ENV_REF)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--image-name", default=DEFAULT_IMAGE_NAME)
    parser.add_argument("--service-name", default=DEFAULT_SERVICE_NAME)
    parser.add_argument("--service-account-id", default=DEFAULT_SERVICE_ACCOUNT_ID)
    parser.add_argument("--invoker-email", default=INVOKER_ENV_REF)
    parser.add_argument("--data-version", default=DEFAULT_DATA_VERSION)
    parser.add_argument("--max-instances", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = build_cloud_run_api_deploy_plan(
        project=args.project,
        project_number=args.project_number,
        region=args.region,
        repository=args.repository,
        image_name=args.image_name,
        service_name=args.service_name,
        service_account_id=args.service_account_id,
        invoker_email=args.invoker_email,
        data_version=args.data_version,
        max_instances=args.max_instances,
    )
    print(render_cloud_run_api_deploy_plan(plan))


if __name__ == "__main__":
    main()
