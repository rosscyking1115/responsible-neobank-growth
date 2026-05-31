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

Example deployment flow:

```bash
export GCP_PROJECT_ID="<project-id>"
export GCP_REGION="europe-west2"
export IMAGE="europe-west2-docker.pkg.dev/${GCP_PROJECT_ID}/neobank/neobank-api:latest"

gcloud artifacts repositories create neobank \
  --repository-format=docker \
  --location="${GCP_REGION}" \
  --description="Neobank portfolio API images"

gcloud builds submit --tag "${IMAGE}" .

gcloud run deploy neobank-api \
  --image="${IMAGE}" \
  --region="${GCP_REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="DATA_VERSION=synthetic-portfolio"
```

For a private production-style service, remove `--allow-unauthenticated` and put
the API behind IAM, an API gateway, or a controlled frontend.

## Scheduled Cloud Run Jobs

For batch scoring and monitoring, use Cloud Run Jobs rather than a long-running
web service. Google Cloud's current pattern is to create Cloud Scheduler HTTP
jobs that call the Cloud Run Jobs `:run` API with an OAuth service account.

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
