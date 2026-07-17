# GCP Warehouse Readiness

This project runs locally on DuckDB by default. The cloud path is a batch
analytics pattern: generate parquet, land it in Cloud Storage, load managed raw
tables in BigQuery, then run dbt against BigQuery datasets.

## Raw Landing Pattern

Generate a reproducible, cloud-ready synthetic export locally:

```powershell
uv run python -m src.cloud.export --profile demo
```

The command writes parquet files and `manifest.json` under
`NEOBANK_CLOUD_EXPORT_DIR`, which defaults to `data/cloud_export/demo`.

Render a checked Cloud Storage upload plan:

```powershell
uv run python -m src.cloud.gcs_upload_plan --manifest data/cloud_export/demo/manifest.json
```

The rendered commands upload those parquet files to a Cloud Storage prefix such
as:

```text
gs://<bucket>/neobank/raw/demo/*.parquet
```

The tracked manifest at `cloud/gcp/raw_bigquery_manifest.json` defines the raw
tables, expected parquet files, partition fields, clustering fields, and load
write mode. Render the load commands with:

```powershell
uv run python -m src.cloud.gcp_load_plan
```

Required variables:

```text
GCP_PROJECT_ID
NEOBANK_BQ_RAW_DATASET
NEOBANK_BQ_LOCATION
NEOBANK_GCS_RAW_BUCKET
NEOBANK_GCS_RAW_PREFIX
```

The rendered commands use BigQuery managed tables rather than external tables so
the downstream dbt marts have stable performance and can use partition pruning.
They are intentionally command renderers first: review them, set environment
variables, authenticate with `gcloud`, then run the commands when you are ready
to create real cloud resources.

Verify the loaded raw tables and row counts:

```powershell
uv run python -m src.cloud.bigquery_verify_plan `
  --project neobank-growth-platform-ross `
  --dataset neobank_raw `
  --expected-export-manifest data/cloud_export/demo/manifest.json
```

The verification plan renders PowerShell-safe `bq` commands. Run the rendered
query after loading the raw tables; every row should have `passed = true`.

## Cost Control and Cleanup

Render the demo cleanup and cost-control plan:

```powershell
uv run python -m src.cloud.gcp_cleanup_plan `
  --project neobank-growth-platform-ross `
  --dataset neobank_raw `
  --bucket neobank-growth-platform-ross-raw `
  --prefix neobank/raw/demo
```

The plan separates non-destructive inventory checks from destructive cleanup
commands. It also renders a Cloud Storage lifecycle command using
`cloud/gcp/gcs_lifecycle_demo.json`, which deletes objects under
`neobank/raw/demo/` after 30 days. Keep the raw demo resources while actively
building the BigQuery/dbt path; run the destructive cleanup commands only when
the live GCP slice is no longer needed.

## Exercised Demo Path

The demo raw landing path was exercised on 2026-05-30 against project
`neobank-growth-platform-ross`:

- 13 generated parquet files uploaded to
  `gs://neobank-growth-platform-ross-raw/neobank/raw/demo/`.
- 13 raw BigQuery tables loaded into `neobank_raw`.
- Manifest row-count verification passed for all 13 raw tables.
- Partitioning and clustering appeared in `bq ls` for the configured fact
  tables.
- dbt build completed against BigQuery with 13 staging views, 3 intermediate
  tables, 12 mart tables, and 107 passing dbt checks.
- Batch activation scores loaded into `neobank_ml.customer_scores_daily` on
  2026-05-31 with 5,000 scored users, 1,390 targeted users, and 191
  vulnerable-customer-review cases.
- The BigQuery score monitoring query returned `monitoring_status = pass` on
  2026-05-31 for the 2025-06-30 score partition.

> **Note (since the responsible-growth pivot).** The figures above record the
> warehouse as exercised on 2026-05-30/31, before the responsible-growth modules
> were added. The data model has since grown to **16 raw tables** — the load
> manifest now also covers `wellbeing_proxies`, `onboarding_events`, and
> `protection_events`, with their `fct_customer_outcomes`, `fct_onboarding_funnel`,
> and `fct_protection_events` marts. These new tables are exercised locally
> (`dbt build`, 133 checks) but have **not** yet been reloaded to BigQuery; the
> counts above will increase on the next GCP run.

This proves the raw GCS-to-BigQuery warehouse path and dbt mart build are
working for a small synthetic demo export. Batch scoring has also been exercised
through Cloud Storage and BigQuery.

> **Scheduled-jobs status (dated history, corrected 2026-07-17).** An earlier
> version of this document stated that scheduled scoring/monitoring jobs "have
> not yet been deployed on GCP". That understated what
> [CLOUD_RUN_DEPLOYMENT.md](CLOUD_RUN_DEPLOYMENT.md) records with execution IDs:
> on **2026-05-31**, Cloud Scheduler triggered both
> `neobank-activation-score-load` and `neobank-score-monitoring` successfully as
> a **one-off smoke test**. What was *not* done is leaving a standing daily
> schedule running, and production security controls remain undeployed. Both
> dated records stand; this note reconciles them rather than rewriting either.
> The current Route C cloud evidence is the dated 2026-07-17 BigQuery benchmark
> run ([artifacts/plan3/run-record.md](../artifacts/plan3/run-record.md)); the
> 2026-05-30/31 figures above are historical.

## BigQuery Dataset Layout

Recommended datasets:

- `neobank_raw`: raw parquet loads from Cloud Storage.
- `neobank_staging`: dbt staging views.
- `neobank_intermediate`: dbt intermediate models.
- `neobank_marts`: product, experiment, pricing, geo, and finance marts.
- `neobank_ml`: activation propensity score extracts and model outputs.
- `neobank_monitoring`: monitoring snapshots and score-distribution checks.

Use one GCP location for the Cloud Storage bucket and BigQuery datasets. BigQuery
loads from Cloud Storage require location compatibility between the bucket and
the destination dataset.

## BigQuery Batch Scores

Generate a daily activation score extract locally:

```powershell
uv run python -m src.modelling.run_activation_model
uv run python -m src.modelling.batch_score_activation --score-date 2025-06-30
```

Then render the GCP upload, dataset, load, and verification commands:

```powershell
$env:NEOBANK_GCS_SCORING_PREFIX="neobank/scoring/activation"
uv run python -m src.cloud.bigquery_score_load_plan `
  --score-date 2025-06-30 `
  --project neobank-growth-platform-ross `
  --dataset neobank_ml `
  --location EU `
  --bucket neobank-growth-platform-ross-raw `
  --prefix "$env:NEOBANK_GCS_SCORING_PREFIX"
```

The score table is loaded as
`neobank_ml.customer_scores_daily`, partitioned by `score_date`, and clustered
by `model_version`, `decision`, and `region`. The demo command uses `--replace`
to keep the portfolio run idempotent. A live scheduled job should use partition
replacement or a merge pattern so re-runs for one score date do not duplicate
rows.

The 2026-05-31 demo verification query returned:

```text
score_date    scored_users    targeted_users    vulnerable_review_users
2025-06-30    5,000           1,390             191
```

Render the matching warehouse-side score monitoring query with:

```powershell
uv run python -m src.cloud.bigquery_score_monitoring_plan `
  --score-date 2025-06-30 `
  --project neobank-growth-platform-ross `
  --dataset neobank_ml `
  --location EU `
  --min-rows 5000
```

The 2026-05-31 score monitoring query returned:

```text
score_date    scored_users    unique_users    model_versions    targeted_users    targeting_rate    vulnerable_review_users    vulnerable_review_rate    monitoring_status
2025-06-30    5,000           5,000           1                 1,390             0.2780            191                        0.0382                    pass
```

To move from manual execution to scheduled operations, render the Cloud Scheduler
plan for the Cloud Run scoring and monitoring jobs:

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

Omit `--score-date` for a rolling daily schedule; keep it for the reproducible
portfolio demo run.

Then render the scheduler triggers:

```powershell
uv run python -m src.cloud.cloud_run_scheduler_plan `
  --project neobank-growth-platform-ross `
  --project-number 319492039091 `
  --run-region europe-west2 `
  --scheduler-region europe-west2 `
  --service-account-email neobank-scheduler@neobank-growth-platform-ross.iam.gserviceaccount.com
```

## dbt BigQuery Target

The default dbt target remains local DuckDB for CI and reproducibility. For a
BigQuery run, install `dbt-bigquery` through the `gcp` extra and use the
`bigquery` target already defined in `dbt_neobank/profiles.yml`. The standalone
`dbt_neobank/profiles.bigquery.example.yml` mirrors the same settings for
copy/paste into another environment:

```yaml
neobank:
  target: bigquery
  outputs:
    bigquery:
      type: bigquery
      method: oauth
      project: "{{ env_var('GCP_PROJECT_ID') }}"
      dataset: "{{ env_var('NEOBANK_BQ_DEFAULT_DATASET', 'neobank_dev') }}"
      location: "{{ env_var('NEOBANK_BQ_LOCATION', 'EU') }}"
      threads: 4
      job_execution_timeout_seconds: 300
      priority: interactive
      maximum_bytes_billed: "{{ env_var('NEOBANK_BQ_MAX_BYTES_BILLED', 1000000000) | as_number }}"
      job_retries: 1
```

BigQuery uses `dataset` where other warehouses often say `schema`, so the dbt
project's `+schema` model settings map naturally to separate BigQuery datasets.
For larger event tables, use date partitioning plus clustering on common filter
dimensions such as region, feature, offer, and merchant category.

For local BigQuery execution, install the adapter extra and point dbt at the
example profile:

```powershell
uv sync --extra gcp --group dev
$env:GCP_PROJECT_ID="neobank-growth-platform-ross"
$env:NEOBANK_BQ_LOCATION="EU"
$env:NEOBANK_BQ_RAW_DATASET="neobank_raw"
$env:NEOBANK_BQ_DEFAULT_DATASET="neobank_dev"
$env:NEOBANK_BQ_DATASET_PREFIX="neobank"
$env:NEOBANK_BQ_MAX_BYTES_BILLED="1000000000"
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank --profile neobank --target bigquery
```

The staging models use `read_parquet(...)` for DuckDB and `source('neobank_raw',
...)` for BigQuery, so the same dbt graph can run against local parquet or the
loaded raw BigQuery tables.

For the BigQuery target, the custom schema macro maps dbt model layers to clean
datasets: `neobank_staging`, `neobank_intermediate`, and `neobank_marts` by
default. Set `NEOBANK_BQ_DATASET_PREFIX` to use a different prefix.

## Operational Notes

- Load raw parquet with `WRITE_TRUNCATE` for a reproducible portfolio snapshot.
- Use append or partition overwrite only after adding incremental source dates.
- Keep Cloud Storage lifecycle rules for generated raw snapshots, especially if
  the same pattern is later used for daily score exports.
- Keep `NEOBANK_BQ_MAX_BYTES_BILLED` low in development and raise it only when
  a larger run is intentional.
- Keep score extracts in a separate Cloud Storage prefix such as
  `neobank/scoring/activation/` so model outputs can have a different lifecycle
  and access policy from raw source files.
- Store service-account credentials outside the repo and pass them through
  environment variables or CI secrets.
- Run dbt tests and the monitoring snapshot after each cloud load.
- Run the BigQuery verification plan after each raw load and keep the output in
  release notes or screenshots when using the project in portfolio material.

## Manual GCP Commands

These steps require a real Google Cloud account, billing/project access, and
local `gcloud` authentication:

```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project <your-project-id>
```

Then set the project, bucket, and prefix in `.env` or the shell before running
the rendered upload and load commands. The repo does not commit credentials,
service-account keys, generated parquet, or `.env` files.

## References

- Google BigQuery Cloud Storage parquet loading:
  https://docs.cloud.google.com/bigquery/docs/loading-data-cloud-storage-parquet
- Google BigQuery partitioned tables:
  https://docs.cloud.google.com/bigquery/docs/partitioned-tables
- Google BigQuery clustered tables:
  https://docs.cloud.google.com/bigquery/docs/clustered-tables
- Google Cloud Storage bucket lifecycle updates:
  https://docs.cloud.google.com/sdk/gcloud/reference/storage/buckets/update
- Google Cloud Storage recursive deletion:
  https://docs.cloud.google.com/sdk/gcloud/reference/storage/rm
- Google BigQuery `bq` command-line reference:
  https://cloud.google.com/bigquery/docs/reference/bq-cli-reference
- Google Cloud Storage lifecycle management:
  https://docs.cloud.google.com/storage/docs/lifecycle
- dbt BigQuery profile setup:
  https://docs.getdbt.com/docs/local/connect-data-platform/bigquery-setup
- dbt BigQuery partitioning and clustering configs:
  https://docs.getdbt.com/reference/resource-configs/bigquery-configs
