# GCP Warehouse Readiness

This project runs locally on DuckDB by default. The cloud path is a batch
analytics pattern: generate parquet, land it in Cloud Storage, load managed raw
tables in BigQuery, then run dbt against BigQuery datasets.

## Raw Landing Pattern

Generate the reproducible synthetic data locally:

```powershell
uv run python -m data_generator.generate --users 50000 --months 12 --output-dir raw/portfolio_full
```

Upload those parquet files to a dated Cloud Storage prefix such as:

```text
gs://<bucket>/neobank/raw/snapshot_date=2025-06-30/*.parquet
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
- Store service-account credentials outside the repo and pass them through
  environment variables or CI secrets.
- Run dbt tests and the monitoring snapshot after each cloud load.

## References

- Google BigQuery Cloud Storage parquet loading:
  https://docs.cloud.google.com/bigquery/docs/loading-data-cloud-storage-parquet
- Google BigQuery partitioned tables:
  https://docs.cloud.google.com/bigquery/docs/partitioned-tables
- Google BigQuery clustered tables:
  https://docs.cloud.google.com/bigquery/docs/clustered-tables
- Google Cloud Storage lifecycle management:
  https://docs.cloud.google.com/storage/docs/lifecycle
- dbt BigQuery profile setup:
  https://docs.getdbt.com/docs/local/connect-data-platform/bigquery-setup
- dbt BigQuery partitioning and clustering configs:
  https://docs.getdbt.com/reference/resource-configs/bigquery-configs
