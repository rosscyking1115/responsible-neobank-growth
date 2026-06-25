# Portfolio Release Notes

## Recruiter Scan

Customer Growth & Pricing Intelligence Platform is a synthetic, end-to-end
product analytics project for a fintech growth/product data science role. It
demonstrates warehouse modelling, experimentation, causal inference, model
decisioning, pricing simulation, monitoring, and dashboarding in one
reproducible repo.

The product-ready upgrade roadmap is documented in `docs/PRODUCT_READY_PLAN.md`;
the repo now includes the public dashboard, API contract, pricing scenario
artifacts, model monitoring, BigQuery/GCS warehouse path, private Cloud Run API,
scheduled Cloud Run batch jobs, Cloud Monitoring alerts, and operational release
gates.

## Suggested CV Bullet

- Built a synthetic fintech customer growth and pricing intelligence platform
  using dbt, DuckDB, BigQuery, Cloud Run, Python, Streamlit, FastAPI, CUPED A/B
  testing, activation modelling, pricing scenarios, and geo incrementality;
  delivered tested marts, model card, scheduled scoring jobs, monitoring alerts,
  API contracts, and a PM-facing dashboard with CI validation.

## Suggested LinkedIn Wording

For a ready-to-post version, use `docs/PUBLIC_LAUNCH.md`.

I built a synthetic fintech customer growth and pricing intelligence platform to
mirror how a modern product data science team works: generate event data, model
trusted dbt marts, run activation and referral analyses, train a guarded
decisioning model, and turn the outputs into a Streamlit dashboard, API
contracts, scheduled scoring jobs, monitoring reports, and pricing scenario
artifacts.

The project covers CUPED experimentation, sample-ratio checks, guardrails,
heterogeneous effects, synthetic-control geo incrementality, placebo tests,
activation model calibration, explainability, private Cloud Run API deployment,
scheduled Cloud Run batch scoring, BigQuery/GCS loading, pricing sensitivity
analysis, and a public-release-ready analytics narrative.

## Demo Script

1. Open the dashboard and show the top-line activation, CLV proxy, onboarding
   lift, and referral economics metrics.
2. Use `docs/CASE_STUDY.md` to frame the product decisions supported before
   moving into technical evidence.
3. Show product health: complete-week WAU, regional D7 activation, week 1+
   post-activation retention, feature adoption, and CLV by income segment.
4. Switch to pricing intelligence and show recommendation actions, offer margin,
   scenario portfolio, and sensitivity checks.
5. Switch to experiments and explain why onboarding ships while referral
   incentives need cheaper unit economics.
6. Point to API docs, Cloud Run deployment evidence, monitoring reports, dbt
   marts, tests, and CI to show a reproducible analytics layer rather than a
   one-off notebook.

## Screenshot Checklist

Recommended portfolio captures:

- Dashboard top metrics and product health.
- Pricing intelligence tab with scenario runs and sensitivity checks.
- Experiments tab with onboarding and referral readouts.
- Monitoring tab with release-gate status.
- Cloud Run API health check and Cloud Monitoring alert policies.
- dbt lineage or docs page after running `dbt docs generate` and `dbt docs serve`.
- CI run showing lint, tests, notebook checks, data generation, and dbt build.

## Quality Gate

Before sharing publicly, run:

```powershell
uv run ruff check .
uv run pytest
uv run marimo check notebooks --ignore-scripts --format json
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank
uv run python -c "from streamlit.testing.v1 import AppTest; at=AppTest.from_file('app/streamlit_app.py'); at.run(timeout=15); print(len(at.exception))"
```
