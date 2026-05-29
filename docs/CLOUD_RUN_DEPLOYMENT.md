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
