from __future__ import annotations

from src.cloud.cloud_run_job_deploy_plan import (
    build_cloud_run_job_deploy_plan,
    render_build_command,
    render_cloud_run_job_deploy_plan,
    render_job_execute_commands,
    render_monitoring_job_create_command,
    render_project_iam_commands,
    render_scoring_job_create_command,
)


def test_job_deploy_plan_builds_image_and_service_account_refs() -> None:
    plan = build_cloud_run_job_deploy_plan(
        project="neobank-growth-platform-ross",
        region="europe-west2",
    )

    assert plan.image_uri == (
        "europe-west2-docker.pkg.dev/neobank-growth-platform-ross/neobank/"
        "neobank-jobs:latest"
    )
    assert plan.service_account_email == (
        "neobank-jobs@neobank-growth-platform-ross.iam.gserviceaccount.com"
    )


def test_job_deploy_commands_create_scoring_and_monitoring_jobs() -> None:
    plan = build_cloud_run_job_deploy_plan(
        project="neobank-growth-platform-ross",
        region="europe-west2",
        bucket="neobank-growth-platform-ross-raw",
        bq_location="EU",
        bq_ml_dataset="neobank_ml",
        bq_monitoring_dataset="neobank_monitoring",
        score_date="2025-06-30",
        users=5000,
        months=6,
    )

    build = render_build_command(plan)
    scoring = render_scoring_job_create_command(plan)
    monitoring = render_monitoring_job_create_command(plan)
    iam = render_project_iam_commands(plan)
    smoke = render_job_execute_commands(plan)

    assert build == (
        "gcloud builds submit --config cloudbuild.jobs.yaml --substitutions "
        "_IMAGE_URI=europe-west2-docker.pkg.dev/neobank-growth-platform-ross/"
        "neobank/neobank-jobs:latest ."
    )
    assert "gcloud run jobs create neobank-activation-score-load" in scoring
    assert "--args=-m,src.cloud.jobs.activation_score_load" in scoring
    assert "NEOBANK_JOB_USERS=5000" in scoring
    assert "NEOBANK_SCORE_DATE=2025-06-30" in scoring
    assert "NEOBANK_SCORE_MONITORING_MIN_ROWS=5000" in scoring
    assert "gcloud run jobs create neobank-score-monitoring" in monitoring
    assert "--args=-m,src.cloud.jobs.score_monitoring" in monitoring
    assert "--role=roles/bigquery.jobUser" in iam[0]
    assert "--role=roles/bigquery.dataEditor" in iam[1]
    assert "--role=roles/storage.objectAdmin" in iam[2]
    assert smoke == [
        "gcloud run jobs execute neobank-activation-score-load --region=europe-west2 --wait",
        "gcloud run jobs execute neobank-score-monitoring --region=europe-west2 --wait",
    ]


def test_render_cloud_run_job_deploy_plan_includes_operator_steps() -> None:
    plan = build_cloud_run_job_deploy_plan()

    rendered = render_cloud_run_job_deploy_plan(plan)

    assert "# Cloud Run Job Deployment Plan" in rendered
    assert "cloudbuild.jobs.yaml" in rendered
    assert "Dockerfile.jobs" in rendered
    assert "src.cloud.jobs.activation_score_load" in rendered
    assert "src.cloud.jobs.score_monitoring" in rendered
    assert "## Create jobs" in rendered
    assert "## Smoke test jobs" in rendered


def test_job_deploy_plan_omits_fixed_score_date_by_default() -> None:
    plan = build_cloud_run_job_deploy_plan(
        project="neobank-growth-platform-ross",
        region="europe-west2",
        bucket="neobank-growth-platform-ross-raw",
    )

    scoring = render_scoring_job_create_command(plan)
    rendered = render_cloud_run_job_deploy_plan(plan)

    assert "NEOBANK_SCORE_DATE=" not in scoring
    assert "Score date: `runtime UTC date`" in rendered
