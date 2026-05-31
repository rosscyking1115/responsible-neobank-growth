"""Render Cloud Scheduler commands for Cloud Run Jobs."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

PROJECT_ENV_REF = "${GCP_PROJECT_ID}"
PROJECT_NUMBER_ENV_REF = "${GCP_PROJECT_NUMBER}"
RUN_REGION_ENV_REF = "${NEOBANK_CLOUD_RUN_REGION}"
SCHEDULER_REGION_ENV_REF = "${NEOBANK_SCHEDULER_REGION}"
SCHEDULER_SERVICE_ACCOUNT_ENV_REF = "${NEOBANK_SCHEDULER_SERVICE_ACCOUNT_EMAIL}"
DEFAULT_TIME_ZONE = "Europe/London"
DEFAULT_SERVICE_ACCOUNT_ID = "neobank-scheduler"


@dataclass(frozen=True)
class ScheduledCloudRunJob:
    scheduler_job_name: str
    cloud_run_job_name: str
    schedule: str
    description: str


@dataclass(frozen=True)
class CloudRunSchedulerPlan:
    project: str
    project_number: str
    run_region: str
    scheduler_region: str
    time_zone: str
    service_account_id: str
    service_account_email: str
    jobs: tuple[ScheduledCloudRunJob, ...]


def default_scheduled_jobs() -> tuple[ScheduledCloudRunJob, ...]:
    return (
        ScheduledCloudRunJob(
            scheduler_job_name="neobank-daily-activation-scoring",
            cloud_run_job_name="neobank-activation-score-load",
            schedule="0 6 * * *",
            description="Run daily activation scoring and BigQuery score load.",
        ),
        ScheduledCloudRunJob(
            scheduler_job_name="neobank-daily-score-monitoring",
            cloud_run_job_name="neobank-score-monitoring",
            schedule="30 6 * * *",
            description="Run daily BigQuery score monitoring after scoring completes.",
        ),
    )


def build_cloud_run_scheduler_plan(
    *,
    project: str = PROJECT_ENV_REF,
    project_number: str = PROJECT_NUMBER_ENV_REF,
    run_region: str = RUN_REGION_ENV_REF,
    scheduler_region: str = SCHEDULER_REGION_ENV_REF,
    time_zone: str = DEFAULT_TIME_ZONE,
    service_account_id: str = DEFAULT_SERVICE_ACCOUNT_ID,
    service_account_email: str = SCHEDULER_SERVICE_ACCOUNT_ENV_REF,
    jobs: tuple[ScheduledCloudRunJob, ...] | None = None,
) -> CloudRunSchedulerPlan:
    return CloudRunSchedulerPlan(
        project=project,
        project_number=project_number,
        run_region=run_region,
        scheduler_region=scheduler_region,
        time_zone=time_zone,
        service_account_id=service_account_id,
        service_account_email=service_account_email,
        jobs=jobs or default_scheduled_jobs(),
    )


def cloud_run_job_uri(plan: CloudRunSchedulerPlan, job: ScheduledCloudRunJob) -> str:
    return (
        "https://run.googleapis.com/v2/projects/"
        f"{plan.project}/locations/{plan.run_region}/jobs/{job.cloud_run_job_name}:run"
    )


def render_enable_services_command() -> str:
    return "gcloud services enable run.googleapis.com cloudscheduler.googleapis.com"


def render_service_account_create_command(plan: CloudRunSchedulerPlan) -> str:
    return " ".join(
        [
            "gcloud iam service-accounts create",
            plan.service_account_id,
            f"--project={plan.project}",
            '--display-name="Neobank Cloud Run job scheduler"',
        ]
    )


def render_run_invoker_binding_command(
    plan: CloudRunSchedulerPlan,
    job: ScheduledCloudRunJob,
) -> str:
    return " ".join(
        [
            "gcloud run jobs add-iam-policy-binding",
            job.cloud_run_job_name,
            f"--region={plan.run_region}",
            f"--member=serviceAccount:{plan.service_account_email}",
            "--role=roles/run.invoker",
        ]
    )


def render_scheduler_create_command(
    plan: CloudRunSchedulerPlan,
    job: ScheduledCloudRunJob,
) -> str:
    return " ".join(
        [
            "gcloud scheduler jobs create http",
            job.scheduler_job_name,
            f"--location={plan.scheduler_region}",
            f'--schedule="{job.schedule}"',
            f'--time-zone="{plan.time_zone}"',
            f'--description="{job.description}"',
            f'--uri="{cloud_run_job_uri(plan, job)}"',
            "--http-method=POST",
            f"--oauth-service-account-email={plan.service_account_email}",
        ]
    )


def render_scheduler_pause_command(plan: CloudRunSchedulerPlan, job: ScheduledCloudRunJob) -> str:
    return (
        "gcloud scheduler jobs pause "
        f"{job.scheduler_job_name} --location={plan.scheduler_region}"
    )


def render_scheduler_resume_command(plan: CloudRunSchedulerPlan, job: ScheduledCloudRunJob) -> str:
    return (
        "gcloud scheduler jobs resume "
        f"{job.scheduler_job_name} --location={plan.scheduler_region}"
    )


def render_scheduler_delete_command(plan: CloudRunSchedulerPlan, job: ScheduledCloudRunJob) -> str:
    return (
        "gcloud scheduler jobs delete "
        f"{job.scheduler_job_name} --location={plan.scheduler_region}"
    )


def render_manual_execute_command(plan: CloudRunSchedulerPlan, job: ScheduledCloudRunJob) -> str:
    return (
        "gcloud run jobs execute "
        f"{job.cloud_run_job_name} --region={plan.run_region} --wait"
    )


def render_cloud_run_scheduler_plan(plan: CloudRunSchedulerPlan) -> str:
    setup_commands = [
        render_enable_services_command(),
        render_service_account_create_command(plan),
    ]
    for job in plan.jobs:
        setup_commands.append(render_run_invoker_binding_command(plan, job))
        setup_commands.append(render_scheduler_create_command(plan, job))

    smoke_commands = [render_manual_execute_command(plan, job) for job in plan.jobs]
    pause_commands = [render_scheduler_pause_command(plan, job) for job in plan.jobs]
    resume_commands = [render_scheduler_resume_command(plan, job) for job in plan.jobs]
    delete_commands = [render_scheduler_delete_command(plan, job) for job in plan.jobs]

    return "\n".join(
        [
            "# Cloud Run Job Scheduler Plan",
            "",
            f"Project: `{plan.project}`",
            f"Project number: `{plan.project_number}`",
            f"Cloud Run region: `{plan.run_region}`",
            f"Scheduler region: `{plan.scheduler_region}`",
            f"Time zone: `{plan.time_zone}`",
            f"Invoker service account ID: `{plan.service_account_id}`",
            f"Invoker service account: `{plan.service_account_email}`",
            "",
            "This plan assumes the Cloud Run jobs already exist. It creates Cloud Scheduler",
            "HTTP triggers that call the Cloud Run Jobs `:run` API with an OAuth token.",
            "Skip the service account creation command if that account already exists.",
            "",
            "Set these environment variables before running the commands:",
            "",
            "- `GCP_PROJECT_ID`",
            "- `GCP_PROJECT_NUMBER`",
            "- `NEOBANK_CLOUD_RUN_REGION`",
            "- `NEOBANK_SCHEDULER_REGION`",
            "- `NEOBANK_SCHEDULER_SERVICE_ACCOUNT_EMAIL`",
            "",
            "## Create schedules",
            "",
            "```powershell",
            *setup_commands,
            "```",
            "",
            "## Manual smoke execution",
            "",
            "```powershell",
            *smoke_commands,
            "```",
            "",
            "## Pause schedules",
            "",
            "```powershell",
            *pause_commands,
            "```",
            "",
            "## Resume schedules",
            "",
            "```powershell",
            *resume_commands,
            "```",
            "",
            "## Delete schedules",
            "",
            "```powershell",
            *delete_commands,
            "```",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Cloud Scheduler commands for scheduled Cloud Run Jobs."
    )
    parser.add_argument("--project", default=PROJECT_ENV_REF)
    parser.add_argument("--project-number", default=PROJECT_NUMBER_ENV_REF)
    parser.add_argument("--run-region", default=RUN_REGION_ENV_REF)
    parser.add_argument("--scheduler-region", default=SCHEDULER_REGION_ENV_REF)
    parser.add_argument("--time-zone", default=DEFAULT_TIME_ZONE)
    parser.add_argument("--service-account-id", default=DEFAULT_SERVICE_ACCOUNT_ID)
    parser.add_argument("--service-account-email", default=SCHEDULER_SERVICE_ACCOUNT_ENV_REF)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = build_cloud_run_scheduler_plan(
        project=args.project,
        project_number=args.project_number,
        run_region=args.run_region,
        scheduler_region=args.scheduler_region,
        time_zone=args.time_zone,
        service_account_id=args.service_account_id,
        service_account_email=args.service_account_email,
    )
    print(render_cloud_run_scheduler_plan(plan))


if __name__ == "__main__":
    main()
