# Cloud Run Deployment

The API container is designed for Cloud Run services. It exposes FastAPI on the
`PORT` environment variable that Cloud Run injects, with `8080` as the local
default.

## Local Container Smoke Test

```powershell
docker build -f Dockerfile.api -t neobank-api .
docker run --rm -p 8080:8080 neobank-api
```

Then check:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8080/health
```

Expected response fields: `status`, `service`, `contract_version`,
`model_version`, and `data_version`.

## Cloud Run Service

The production-style API path uses a dedicated Cloud Build config for
`Dockerfile.api` and deploys the service private-by-default. Render the reviewed
command plan with:

```powershell
uv run python -m src.cloud.cloud_run_api_deploy_plan `
  --project neobank-growth-platform-ross `
  --project-number 319492039091 `
  --region europe-west2 `
  --invoker-email rosscyking@gmail.com
```

The plan creates or reuses:

- Artifact Registry repository: `neobank`.
- Runtime service account: `neobank-api`.
- Cloud Build image: `europe-west2-docker.pkg.dev/.../neobank-api:latest`.
- Private Cloud Run service: `neobank-api`.
- `roles/run.invoker` for the configured reviewer email.

It also renders an authenticated `/health` smoke test using
`gcloud auth print-identity-token`.

Equivalent deployment flow:

```bash
export GCP_PROJECT_ID="<project-id>"
export GCP_REGION="europe-west2"
export IMAGE="europe-west2-docker.pkg.dev/${GCP_PROJECT_ID}/neobank/neobank-api:latest"

gcloud artifacts repositories create neobank \
  --repository-format=docker \
  --location="${GCP_REGION}" \
  --description="Neobank portfolio API images"

gcloud builds submit \
  --config cloudbuild.api.yaml \
  --substitutions "_IMAGE_URI=${IMAGE}" .

gcloud run deploy neobank-api \
  --image="${IMAGE}" \
  --region="${GCP_REGION}" \
  --platform=managed \
  --service-account="neobank-api@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --no-allow-unauthenticated \
  --set-env-vars="DATA_VERSION=synthetic-portfolio,NEOBANK_ENV=gcp"
```

For a public portfolio demo API, you can deliberately switch to
`--allow-unauthenticated`, but the safer default is IAM-protected Cloud Run with
a small set of explicit invokers. Google Cloud's `gcloud run deploy` supports
`--[no-]allow-unauthenticated`, and Cloud Run service access is granted with
`gcloud run services add-iam-policy-binding ... --role=roles/run.invoker`.

## Scheduled Cloud Run Jobs

For batch scoring and monitoring, use Cloud Run Jobs rather than a long-running
web service. Google Cloud's current pattern is to create Cloud Scheduler HTTP
jobs that call the Cloud Run Jobs `:run` API with an OAuth service account.

This repo includes a job image and two runnable job entrypoints:

- `Dockerfile.jobs` packages the synthetic generator, dbt project, model code,
  and Google Cloud client libraries.
- `src.cloud.jobs.activation_score_load` generates a deterministic synthetic
  slice, builds the DuckDB marts, trains the activation model, writes a daily
  score parquet, uploads it to Cloud Storage, and loads
  `neobank_ml.customer_scores_daily` in BigQuery.
- `src.cloud.jobs.score_monitoring` runs the BigQuery score monitoring query,
  writes the result to `neobank_monitoring.score_monitoring_daily`, and fails
  the job if monitoring status is `fail`.

Render the Cloud Run Job deployment commands with:

```powershell
uv run python -m src.cloud.cloud_run_job_deploy_plan `
  --project neobank-growth-platform-ross `
  --project-number 319492039091 `
  --region europe-west2 `
  --bucket neobank-growth-platform-ross-raw `
  --bq-location EU `
  --bq-ml-dataset neobank_ml `
  --bq-monitoring-dataset neobank_monitoring `
  --score-date 2025-06-30 `
  --users 5000 `
  --months 6
```

The deploy plan renders commands for Artifact Registry, Cloud Build with
`cloudbuild.jobs.yaml`, the job service account, IAM bindings, Cloud Run Job
creation, and manual job smoke tests.

For a rolling daily schedule, omit `--score-date` so the jobs use the runtime UTC
date. Keep `--score-date 2025-06-30` only for reproducible portfolio smoke tests.

Render the scheduler commands with:

```powershell
uv run python -m src.cloud.cloud_run_scheduler_plan `
  --project neobank-growth-platform-ross `
  --project-number 319492039091 `
  --run-region europe-west2 `
  --scheduler-region europe-west2 `
  --service-account-email neobank-scheduler@neobank-growth-platform-ross.iam.gserviceaccount.com
```

The default plan schedules two Cloud Run Jobs:

- `neobank-activation-score-load` at 06:00 Europe/London.
- `neobank-score-monitoring` at 06:30 Europe/London.

Before creating schedules, deploy those Cloud Run Jobs and grant the scheduler
service account `roles/run.invoker` on each job. The rendered plan includes IAM
binding commands, scheduler creation commands, manual smoke execution commands,
and pause/resume/delete commands for rollback.

Deployment evidence from the demo GCP project on 2026-05-31:

- `neobank-activation-score-load` completed as a manual Cloud Run Job execution:
  `neobank-activation-score-load-khjjs`.
- `neobank-score-monitoring` completed as a manual Cloud Run Job execution:
  `neobank-score-monitoring-tl447`.
- Cloud Scheduler triggered `neobank-activation-score-load-6459k` successfully
  using `neobank-scheduler@neobank-growth-platform-ross.iam.gserviceaccount.com`.
- Cloud Scheduler triggered `neobank-score-monitoring-2pjlb` successfully using
  the same scheduler service account.

For the rolling daily schedule, remove `NEOBANK_SCORE_DATE` from both Cloud Run
Jobs so the scoring and monitoring jobs use the runtime UTC date. Keep
`NEOBANK_SCORE_DATE=2025-06-30` only for reproducible smoke tests.

Reference docs:

- Cloud Run jobs on a schedule:
  <https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule>
- Cloud Run job execution:
  <https://docs.cloud.google.com/run/docs/execute/jobs>

## Runtime Configuration

- `PORT`: injected by Cloud Run; defaults to `8080` locally.
- `NEOBANK_ACTIVATION_MODEL_REGISTRY`: optional path to the activation model
  registry JSON. If unset, the service uses deterministic baseline scoring.
- `NEOBANK_DUCKDB_PATH`: optional local DuckDB path for pricing mart-backed
  scenario calibration. In Cloud Run, prefer BigQuery-backed service logic before
  using this in production.

## Release Gate

The GitHub Actions quality job builds the API image and starts the container
locally, then calls `/health`. That keeps the public repo honest: every merged
change must still produce a runnable API container.

## Rollback

Cloud Run keeps revisions. Roll back by routing traffic to the previous healthy
revision:

```bash
gcloud run services update-traffic neobank-api \
  --region="${GCP_REGION}" \
  --to-revisions="<previous-revision>=100"
```

Use monitoring status, API health, pricing guardrail failures, and model-card
changes as rollback triggers.
