# Batch Scoring

Batch scoring turns the trained activation model into a daily customer-score
extract. The output is local parquet by default so it can later be moved to
BigQuery, Cloud Storage, or a Cloud Run job without changing the scoring
contract.

## Generate Model Artifact

```powershell
uv run python -m src.modelling.run_activation_model
```

This writes an ignored registry at:

```text
artifacts/models/activation/registry.json
```

## Write Daily Scores

```powershell
uv run python -m src.modelling.batch_score_activation --score-date 2025-06-30
```

Default output:

```text
artifacts/scoring/activation/score_date=2025-06-30/customer_scores_daily.parquet
```

## Output Columns

- `score_date`
- `user_id`
- `signup_date`
- `model_version`
- `activation_probability`
- `activation_threshold`
- `decision`
- `vulnerable_customer_review`
- `income_segment`
- `signup_channel`
- `region`

The `decision` field is intentionally conservative. Vulnerable customers are not
directly targeted by the batch output; they stay in `monitor` with
`vulnerable_customer_review=true` when their score is below the activation-help
threshold.

## BigQuery Load Plan

After generating the score extract, render the reviewed GCP commands that upload
the parquet file to Cloud Storage and load it into a partitioned BigQuery table:

```powershell
uv run python -m src.cloud.bigquery_score_load_plan --score-date 2025-06-30
```

The default BigQuery destination is:

```text
${GCP_PROJECT_ID}:${NEOBANK_BQ_ML_DATASET}.customer_scores_daily
```

The default Cloud Storage destination is:

```text
gs://${NEOBANK_GCS_RAW_BUCKET}/${NEOBANK_GCS_SCORING_PREFIX}/score_date=2025-06-30/customer_scores_daily.parquet
```

Set `NEOBANK_GCS_SCORING_PREFIX=neobank/scoring/activation` for the demo GCP
path. The rendered `bq load` command creates a managed table partitioned by
`score_date` and clustered by `model_version`, `decision`, and `region`.
