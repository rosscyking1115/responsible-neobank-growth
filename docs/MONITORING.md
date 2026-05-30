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

## Scheduled Monitoring Workflow

The repository includes a GitHub Actions workflow at
`.github/workflows/monitoring-snapshot.yml` that can run manually or on a weekly
schedule. It rebuilds a deterministic synthetic warehouse, trains the activation
model artifact, generates batch activation scores, writes the product monitoring
snapshot, writes the activation model monitoring report, and uploads the
monitoring/scoring outputs as workflow artifacts.

Run it from GitHub Actions with **Monitoring Snapshot > Run workflow** before a
portfolio refresh or public demo review. The workflow is intentionally synthetic:
it proves the operational path without requiring real customer data, secrets, or
cloud warehouse credentials.

On a first run, the activation model monitoring report can return `warn` for
score-distribution drift because no previous score extract exists yet. In a live
setup, the previous successful artifact or warehouse score table would be passed
as the reference extract.

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

## Realised-Label Calibration Monitoring

After D7 outcomes have matured for a scored cohort, generate the calibration
report by joining score extracts to realised activation labels:

```powershell
uv run python -m src.monitoring.calibration_report `
  --score-path artifacts/scoring/activation/score_date=2025-06-30/customer_scores_daily.parquet `
  --db neobank.duckdb `
  --report-date 2025-07-07
```

You can also provide a label extract with `--label-path` when labels are exported
from a warehouse table. The file must contain `user_id` and `activated_d7`.

Default output:

```text
artifacts/monitoring/model_activation_calibration/report_date=2025-07-07/activation_calibration_monitoring.json
artifacts/monitoring/model_activation_calibration/report_date=2025-07-07/activation_calibration_monitoring.md
```

The calibration report checks matched label coverage, sample size, expected
calibration error, Brier score, portfolio prediction bias, and the largest
segment calibration gap across income segment, signup channel, and region. Run
this after the prediction window closes; before then, use the score-distribution
report as the early-warning signal.

## Operational Policy

Use this lightweight release gate before refreshing public screenshots or
ramping a synthetic rollout:

1. Run `dbt build`.
2. Generate batch activation scores.
3. Run the monitoring snapshot.
4. Run the score-distribution report against a recent reference extract.
5. After D7 labels mature, run the calibration report.

Stop the release when any report returns `fail`. Review the affected check,
regenerate upstream data only if the failure is caused by stale local artifacts,
and document the decision before continuing. Treat `warn` as a human-review
state: acceptable for a demo when explained, but not for an unattended rollout.
