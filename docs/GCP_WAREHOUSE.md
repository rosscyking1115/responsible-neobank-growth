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

This proves the raw GCS-to-BigQuery warehouse path is working for a small
synthetic demo export. It does not yet mean the dbt mart layer has been ported
and run on BigQuery.

## BigQuery Dataset Layout

Recommended datasets:

- `neobank_raw`: raw parquet loads from Cloud Storage.
- `neobank_staging`: dbt staging views.
- `neobank_intermediate`: dbt intermediate models.
- `neobank_marts`: product, experiment, pricing, geo, and finance marts.
- `neobank_monitoring`: monitoring snapshots and score-distribution checks.

Use one GCP location for the Cloud Storage bucket and BigQuery datasets. BigQuery
loads from Cloud Storage require location compatibility between the bucket and
the destination dataset.

## dbt BigQuery Target

Keep `dbt_neobank/profiles.yml` local-only for CI. For a BigQuery run, install
`dbt-bigquery` in the execution environment and use the example profile at
`dbt_neobank/profiles.bigquery.example.yml`:

```yaml
neobank:
  target: bigquery
  outputs:
    bigquery:
      type: bigquery
      method: service-account
      project: "{{ env_var('GCP_PROJECT_ID') }}"
      dataset: "{{ env_var('NEOBANK_BQ_STAGING_DATASET', 'neobank_staging') }}"
      location: "{{ env_var('NEOBANK_BQ_LOCATION', 'EU') }}"
      keyfile: "{{ env_var('GOOGLE_APPLICATION_CREDENTIALS') }}"
      threads: 4
      timeout_seconds: 300
      priority: interactive
```

BigQuery uses `dataset` where other warehouses often say `schema`, so the dbt
project's `+schema` model settings map naturally to separate BigQuery datasets.
For larger event tables, use date partitioning plus clustering on common filter
dimensions such as region, feature, offer, and merchant category.

## Operational Notes

- Load raw parquet with `WRITE_TRUNCATE` for a reproducible portfolio snapshot.
- Use append or partition overwrite only after adding incremental source dates.
- Keep Cloud Storage lifecycle rules for generated raw snapshots, especially if
  the same pattern is later used for daily score exports.
- Keep `NEOBANK_BQ_MAX_BYTES_BILLED` low in development and raise it only when
  a larger run is intentional.
- Store service-account credentials outside the repo and pass them through
  environment variables or CI secrets.
- Run dbt tests and the monitoring snapshot after each cloud load.
- Run the BigQuery verification plan after each raw load and keep the output in
  release notes or screenshots when using the project in portfolio material.

## What Ross Must Run Locally For Real GCP

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
