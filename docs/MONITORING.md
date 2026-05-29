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
