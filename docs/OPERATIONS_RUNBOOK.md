# Operations Runbook

This runbook describes the local release checks for the synthetic Customer Growth
& Pricing Intelligence Platform. It is written as if the product were operated by
a small fintech analytics team, while keeping every step reproducible without
private cloud credentials.

## Release Gate

Run these checks before a public demo refresh, LinkedIn screenshot update, or
cloud deployment attempt:

```powershell
uv run ruff check .
uv run pytest
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank
uv run python -m src.modelling.run_activation_model
uv run python -m src.modelling.batch_score_activation --score-date 2025-06-30
uv run python -m src.cloud.bigquery_score_load_plan --score-date 2025-06-30
uv run python -m src.monitoring.snapshot --snapshot-date 2025-06-30
uv run python -m src.monitoring.model_report --report-date 2025-06-30
```

After D7 outcomes are available for the scored cohort, run:

```powershell
uv run python -m src.monitoring.calibration_report `
  --score-path artifacts/scoring/activation/score_date=2025-06-30/customer_scores_daily.parquet `
  --db neobank.duckdb `
  --report-date 2025-07-07
```

## Status Policy

- `pass`: continue.
- `warn`: continue only after a human review note explains why the risk is
  acceptable for the current use.
- `fail`: stop the release or rollout until the cause is fixed.

## Rollback Triggers

Rollback or disable model-backed targeting when any of these checks fail:

- dbt marts required by dashboard, API, pricing, or monitoring are missing.
- Activation score extracts are missing or materially smaller than expected.
- Score probabilities fall outside the 0 to 1 range.
- Targeting rate moves outside the configured operating band.
- Vulnerable-customer review load exceeds the monitoring threshold.
- Score-distribution PSI exceeds the fail threshold against the reference
  extract.
- Realised-label calibration fails on expected calibration error, Brier score,
  portfolio bias, or segment calibration gap.
- Pricing recommendation guardrails show negative economics, high complaint
  rate, or excessive human-review load.

## Triage

1. Confirm whether the failing artifact is stale by checking the report path and
   generation date.
2. Rebuild dbt and regenerate the affected artifact once.
3. If the failure repeats, inspect the Markdown report and identify the first
   failed check by dependency order: marts, scores, drift, calibration, pricing,
   API readiness.
4. For data failures, fix the generator, dbt model, or schema contract before
   rerunning.
5. For model failures, keep the deterministic baseline API path available,
   retrain the activation artifact, and compare calibration before restoring the
   model-backed registry.

## Cloud Operations Mapping

The local commands map cleanly to a future GCP deployment:

- dbt build: Cloud Build or GitHub Actions job against BigQuery.
- Batch scoring: Cloud Run job writing daily score extracts, with GCS landing
  and BigQuery `customer_scores_daily` loads.
- Monitoring snapshot: Cloud Run job writing JSON and Markdown reports.
- Calibration report: delayed Cloud Run job after D7 labels mature.
- API health: Cloud Run service `/health` plus container smoke test.

The repo keeps DuckDB as the default so reviewers can reproduce the full product
without credentials. Cloud-specific steps should always keep a local fallback.
