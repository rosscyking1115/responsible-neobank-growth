from __future__ import annotations

from src.cloud.cloud_run_api_deploy_plan import (
    build_cloud_run_api_deploy_plan,
    render_authenticated_health_check_commands,
    render_build_command,
    render_cloud_run_api_deploy_plan,
    render_invoker_binding_command,
    render_service_deploy_command,
)


def test_api_deploy_plan_builds_image_and_service_account_refs() -> None:
    plan = build_cloud_run_api_deploy_plan(
        project="neobank-growth-platform-ross",
        region="europe-west2",
    )

    assert plan.image_uri == (
        "europe-west2-docker.pkg.dev/neobank-growth-platform-ross/neobank/"
        "neobank-api:latest"
    )
    assert plan.service_account_email == (
        "neobank-api@neobank-growth-platform-ross.iam.gserviceaccount.com"
    )


def test_api_deploy_commands_are_private_by_default() -> None:
    plan = build_cloud_run_api_deploy_plan(
        project="neobank-growth-platform-ross",
        region="europe-west2",
        invoker_email="rosscyking@gmail.com",
        data_version="synthetic-portfolio",
        max_instances=2,
    )

    build = render_build_command(plan)
    deploy = render_service_deploy_command(plan)
    invoker = render_invoker_binding_command(plan)
    smoke = render_authenticated_health_check_commands(plan)

    assert build == (
        "gcloud builds submit --config cloudbuild.api.yaml --substitutions "
        "_IMAGE_URI=europe-west2-docker.pkg.dev/neobank-growth-platform-ross/"
        "neobank/neobank-api:latest ."
    )
    assert "gcloud run deploy neobank-api" in deploy
    assert "--no-allow-unauthenticated" in deploy
    assert "--ingress=all" in deploy
    assert (
        "--service-account=neobank-api@neobank-growth-platform-ross.iam.gserviceaccount.com"
        in deploy
    )
    assert "--set-env-vars='^@^DATA_VERSION=synthetic-portfolio@NEOBANK_ENV=gcp'" in deploy
    assert invoker == (
        "gcloud run services add-iam-policy-binding neobank-api "
        "--region=europe-west2 --member=user:rosscyking@gmail.com "
        "--role=roles/run.invoker"
    )
    assert smoke == [
        (
            "$SERVICE_URL = gcloud run services describe neobank-api "
            '--region=europe-west2 --format="value(status.url)"'
        ),
        "$TOKEN = gcloud auth print-identity-token",
        'Invoke-RestMethod -Headers @{Authorization="Bearer $TOKEN"} "$SERVICE_URL/health"',
    ]


def test_render_cloud_run_api_deploy_plan_includes_operator_steps() -> None:
    plan = build_cloud_run_api_deploy_plan()

    rendered = render_cloud_run_api_deploy_plan(plan)

    assert "# Cloud Run API Deployment Plan" in rendered
    assert "cloudbuild.api.yaml" in rendered
    assert "Dockerfile.api" in rendered
    assert "## Deploy API" in rendered
    assert "## Authenticated Smoke Test" in rendered
