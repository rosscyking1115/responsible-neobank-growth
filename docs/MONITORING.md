# Monitoring

Generate a local monitoring snapshot after building the DuckDB marts:

```powershell
uv run python -m src.monitoring.snapshot --snapshot-date 2025-06-30
```

Default output:

```text
artifacts/monitoring/snapshot_date=2025-06-30/monitoring_snapshot.json
artifacts/monitoring/snapshot_date=2025-06-30/monitoring_snapshot.md
```

The snapshot checks:

- DuckDB mart availability.
- Activation rate and activation mart freshness.
- Experiment support, complaint, and app-crash guardrails.
- Pricing exposure coverage, net margin, complaint rate, and human-review load.
- Pricing recommendation coverage.
- Activation batch score extract availability.
- API contract file readiness.

`fail` means the release should stop. `warn` means the project can still run, but
the result needs human review before a public release or ramp-up.

The Streamlit dashboard also includes a Monitoring tab that computes the same
snapshot against the current DuckDB path and shows the overall status, status
counts, attention items, and full check table.

## Activation Model Monitoring

After generating daily activation scores, create a model monitoring report:

```powershell
uv run python -m src.monitoring.model_report --report-date 2025-06-30
```

For score-distribution drift, pass a previous score extract as the reference:

```powershell
uv run python -m src.monitoring.model_report `
  --score-path artifacts/scoring/activation/score_date=2025-06-30/customer_scores_daily.parquet `
  --reference-score-path artifacts/scoring/activation/score_date=2025-06-23/customer_scores_daily.parquet `
  --report-date 2025-06-30
```

Default output:

```text
artifacts/monitoring/model_activation/report_date=2025-06-30/activation_model_monitoring.json
artifacts/monitoring/model_activation/report_date=2025-06-30/activation_model_monitoring.md
```

The model report checks probability bounds, score volume, targeting rate,
vulnerable-customer review load, threshold validity, and score-distribution PSI.
Use `fail` as a release stop, and use `warn` as a human-review trigger before a
rollout or public demo refresh.
