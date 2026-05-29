# Portfolio Release Notes

## Recruiter Scan

Customer Growth & Pricing Intelligence Platform is a synthetic, end-to-end
product analytics project for a fintech growth/product data science role. It
demonstrates warehouse modelling, experimentation, causal inference, model
decisioning, dashboarding, and executive communication in one reproducible repo.

The product-ready upgrade roadmap is documented in `docs/PRODUCT_READY_PLAN.md`.
It should be treated as the build plan for the BigQuery, Cloud Run API, pricing
intelligence, batch scoring, and monitoring layers rather than claimed as already
shipped work.

## Suggested CV Bullet

- Built a Monzo-inspired neobank analytics case study using synthetic event data,
  dbt, DuckDB, Python, Streamlit, CUPED A/B testing, activation modelling, and
  geo incrementality; delivered tested marts, decision memos, model card, and a
  PM-facing dashboard with CI validation.

## Suggested LinkedIn Wording

I built a synthetic neobank product analytics project to mirror how a modern
fintech growth data team works: generate event data, model trusted dbt marts, run
activation and referral analyses, train a decisioning model with guardrails, and
turn the outputs into a Streamlit dashboard plus one-page decision memos.

The project covers CUPED experimentation, sample-ratio checks, guardrails,
heterogeneous effects, synthetic-control geo incrementality, placebo tests,
activation model calibration, explainability, and a public-release-ready analytics
narrative.

## Demo Script

1. Open the dashboard and show the top-line activation, CLV proxy, onboarding
   lift, and referral economics metrics.
2. Show product health: complete-week WAU, regional D7 activation, week 1+
   post-activation retention, feature adoption, and CLV by income segment.
3. Switch to experiments and explain why onboarding ships while referral incentives
   need cheaper unit economics.
4. Open the memo files in `docs/memos/` and show how the same analysis becomes
   executive recommendations.
5. Point to dbt marts, tests, and CI to show that the dashboard is backed by a
   reproducible analytics layer rather than a one-off notebook.

## Screenshot Checklist

Recommended portfolio captures:

- Dashboard top metrics and product health.
- Experiments tab with onboarding and referral readouts.
- Decision memos with the two one-page recommendations.
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
