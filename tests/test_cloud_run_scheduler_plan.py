from __future__ import annotations

from src.cloud.cloud_run_scheduler_plan import (
    ScheduledCloudRunJob,
    build_cloud_run_scheduler_plan,
    cloud_run_job_uri,
    default_scheduled_jobs,
    render_cloud_run_scheduler_plan,
    render_manual_execute_command,
    render_run_invoker_binding_command,
    render_scheduler_create_command,
    render_scheduler_delete_command,
    render_scheduler_pause_command,
    render_scheduler_resume_command,
    render_service_account_create_command,
)


def test_default_scheduled_jobs_cover_scoring_and_monitoring() -> None:
    jobs = default_scheduled_jobs()

    assert [job.scheduler_job_name for job in jobs] == [
        "neobank-daily-activation-scoring",
        "neobank-daily-score-monitoring",
    ]
    assert jobs[0].cloud_run_job_name == "neobank-activation-score-load"
    assert jobs[1].cloud_run_job_name == "neobank-score-monitoring"
    assert jobs[0].schedule == "0 6 * * *"
    assert jobs[1].schedule == "30 6 * * *"


def test_cloud_run_job_uri_uses_v2_jobs_run_endpoint() -> None:
    plan = build_cloud_run_scheduler_plan(
        project="neobank-growth-platform-ross",
        run_region="europe-west2",
    )
    job = ScheduledCloudRunJob(
        scheduler_job_name="daily-score",
        cloud_run_job_name="neobank-activation-score-load",
        schedule="0 6 * * *",
        description="Daily score load.",
    )

    assert cloud_run_job_uri(plan, job) == (
        "https://run.googleapis.com/v2/projects/neobank-growth-platform-ross/"
        "locations/europe-west2/jobs/neobank-activation-score-load:run"
    )


def test_render_scheduler_create_command_uses_oauth_service_account() -> None:
    plan = build_cloud_run_scheduler_plan(
        project="neobank-growth-platform-ross",
        run_region="europe-west2",
        scheduler_region="europe-west2",
        service_account_email="neobank-scheduler@neobank-growth-platform-ross.iam.gserviceaccount.com",
    )
    job = plan.jobs[0]

    command = render_scheduler_create_command(plan, job)

    assert command.startswith("gcloud scheduler jobs create http")
    assert "--location=europe-west2" in command
    assert '--schedule="0 6 * * *"' in command
    assert '--time-zone="Europe/London"' in command
    assert "--http-method=POST" in command
    assert (
        "--oauth-service-account-email=neobank-scheduler@"
        "neobank-growth-platform-ross.iam.gserviceaccount.com"
    ) in command
    assert (
        "https://run.googleapis.com/v2/projects/neobank-growth-platform-ross/"
        "locations/europe-west2/jobs/neobank-activation-score-load:run"
    ) in command


def test_render_operational_commands_cover_iam_smoke_pause_resume_delete() -> None:
    plan = build_cloud_run_scheduler_plan(
        project="neobank-growth-platform-ross",
        run_region="europe-west2",
        scheduler_region="europe-west2",
        service_account_email="neobank-scheduler@neobank-growth-platform-ross.iam.gserviceaccount.com",
    )
    job = plan.jobs[0]

    assert render_run_invoker_binding_command(plan, job) == (
        "gcloud run jobs add-iam-policy-binding neobank-activation-score-load "
        "--region=europe-west2 "
        "--member=serviceAccount:neobank-scheduler@"
        "neobank-growth-platform-ross.iam.gserviceaccount.com "
        "--role=roles/run.invoker"
    )
    assert render_manual_execute_command(plan, job) == (
        "gcloud run jobs execute neobank-activation-score-load --region=europe-west2 --wait"
    )
    assert render_service_account_create_command(plan) == (
        "gcloud iam service-accounts create neobank-scheduler "
        "--project=neobank-growth-platform-ross "
        '--display-name="Neobank Cloud Run job scheduler"'
    )
    assert render_scheduler_pause_command(plan, job) == (
        "gcloud scheduler jobs pause neobank-daily-activation-scoring --location=europe-west2"
    )
    assert render_scheduler_resume_command(plan, job) == (
        "gcloud scheduler jobs resume neobank-daily-activation-scoring --location=europe-west2"
    )
    assert render_scheduler_delete_command(plan, job) == (
        "gcloud scheduler jobs delete neobank-daily-activation-scoring --location=europe-west2"
    )


def test_render_cloud_run_scheduler_plan_includes_both_jobs_and_env_contract() -> None:
    plan = build_cloud_run_scheduler_plan()

    rendered = render_cloud_run_scheduler_plan(plan)

    assert "# Cloud Run Job Scheduler Plan" in rendered
    assert "`NEOBANK_SCHEDULER_SERVICE_ACCOUNT_EMAIL`" in rendered
    assert "gcloud iam service-accounts create neobank-scheduler" in rendered
    assert "neobank-daily-activation-scoring" in rendered
    assert "neobank-daily-score-monitoring" in rendered
    assert "gcloud services enable run.googleapis.com cloudscheduler.googleapis.com" in rendered
    assert "## Manual smoke execution" in rendered
    assert "## Pause schedules" in rendered
    assert "## Resume schedules" in rendered
    assert "## Delete schedules" in rendered
