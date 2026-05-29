# Pricing Scenario Runs

The pricing scenario runner turns the `/simulate/pricing` contract into a
persisted decision artifact. It evaluates a portfolio of incentive levels across
income segments, writes the scenario table, and adds sensitivity rows for margin
downside/upside and vulnerable-customer-share stress.

## Run

```powershell
uv run python -m src.pricing.scenario_runs --run-date 2025-06-30
```

With a custom incentive grid:

```powershell
uv run python -m src.pricing.scenario_runs `
  --run-date 2025-06-30 `
  --incentives 0 2 4 6 8
```

Default output:

```text
artifacts/pricing/scenario_runs/run_date=2025-06-30/pricing_scenario_run.json
artifacts/pricing/scenario_runs/run_date=2025-06-30/pricing_scenario_run.md
artifacts/pricing/scenario_runs/run_date=2025-06-30/pricing_scenarios.csv
artifacts/pricing/scenario_runs/run_date=2025-06-30/pricing_sensitivity.csv
```

## Inputs

When `neobank.duckdb` exists and contains the dbt marts, the runner derives
segment priors from:

- `main_marts.fct_activation` for eligible customers, D7 activation, and
  vulnerable-customer share.
- `main_marts.fct_user_clv_proxy` for expected monthly margin assumptions.
- `main_marts.mart_pricing_recommendations` indirectly through the API scenario
  simulator when pricing-mart evidence is available.

If the DuckDB file is missing, the runner falls back to conservative synthetic
segment priors so the public repo remains reproducible without generated data.

## Decision Policy

- `ship`: candidate for a controlled rollout, subject to monitoring.
- `iterate`: candidate for a smaller experiment or cheaper incentive design.
- `hold`: stop state until economics or guardrails improve.

Review the sensitivity CSV before choosing a scenario. A scenario that looks
good only in the base case but fails under margin downside or vulnerable-customer
stress should stay in experiment design, not rollout.
