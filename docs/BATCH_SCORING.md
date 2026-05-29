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
