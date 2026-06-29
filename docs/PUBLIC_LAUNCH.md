# Public Launch Pack

Use this pack when posting the project publicly or tailoring it for job
applications. The wording is designed for product data science, growth analytics,
pricing science, and analytics engineering roles.

## GitHub Summary

Repository description:

```text
Synthetic fintech customer growth and pricing intelligence platform with dbt, DuckDB, Python, Streamlit, FastAPI, experimentation, activation modelling, geo-lift, monitoring, and scenario analysis.
```

Suggested topics:

```text
product-analytics, fintech, dbt, duckdb, streamlit, fastapi, experimentation,
causal-inference, pricing-analytics, machine-learning, monitoring, python, sql
```

## LinkedIn Post

```text
I’ve just finished building a synthetic fintech data product: Customer Growth & Pricing Intelligence Platform.

The project simulates how a modern growth/product data science team might work inside a neobank: generate event data, build trusted dbt marts, analyse activation and referral experiments, train a guarded activation decisioning model, expose API contracts, and turn the outputs into a Streamlit dashboard.

What it covers:
- Product analytics: activation, retention, engagement, feature adoption, CLV proxy.
- Experimentation: CUPED A/B testing, SRM checks, guardrails, heterogeneous effects.
- Causal inference: regional referral incrementality with DiD, synthetic control, and placebo checks.
- ML decisioning: calibrated activation model, model card, batch scoring, score drift, and realised-label calibration monitoring.
- Pricing intelligence: offer economics, guarded recommendations, persisted incentive scenario runs, and sensitivity analysis.
- Productisation: private Cloud Run API, scheduled Cloud Run batch jobs, BigQuery/GCS warehouse path, Cloud Monitoring alerts, CI, and operational runbook.

All data is synthetic. The goal was to build something closer to a small data product than a notebook: reproducible warehouse, tested code, dashboard, API boundary, scheduled scoring, monitoring, and business-facing decision outputs.

Repo: https://github.com/rosscyking1115/responsible-neobank-growth
Dashboard: https://neobank-appuct-analytics.streamlit.app/
Case study: https://github.com/rosscyking1115/responsible-neobank-growth/blob/main/docs/CASE_STUDY.md
```

Shorter version:

```text
I built a synthetic fintech Customer Growth & Pricing Intelligence Platform using Python, SQL, dbt, DuckDB, Streamlit and FastAPI.

It covers activation and retention analytics, CUPED experimentation, geo-lift analysis, activation modelling, pricing scenario simulation, monitoring reports, and a PM-facing dashboard.

The goal was to make a portfolio project that behaves like a small data product: reproducible marts, tested code, API contracts, batch scoring, cloud deployment evidence, model monitoring, pricing sensitivity outputs, and clear product decisions.

All data is synthetic.
Repo: https://github.com/rosscyking1115/responsible-neobank-growth
Dashboard: https://neobank-appuct-analytics.streamlit.app/
Case study: https://github.com/rosscyking1115/responsible-neobank-growth/blob/main/docs/CASE_STUDY.md
```

## CV Bullet

```text
Built a synthetic fintech customer growth and pricing intelligence platform using Python, SQL, dbt, DuckDB, Streamlit, FastAPI, scikit-learn, BigQuery and Cloud Run, modelling activation, retention, CLV proxy, referral incrementality, pricing scenarios and guarded decisioning with CI-tested marts, APIs, scheduled scoring, monitoring alerts and product dashboards.
```

Shorter CV version:

```text
Built a synthetic fintech growth analytics platform with dbt, DuckDB, Python, Streamlit, FastAPI, BigQuery and Cloud Run, covering experimentation, activation modelling, pricing scenarios, geo incrementality, monitoring and product dashboarding.
```

## Portfolio Demo Script

1. Start with the README and explain that the project is synthetic and
   reproducible.
2. Open the case study and frame the business decisions the product supports.
3. Open the dashboard and show the four product surfaces: Product health,
   Pricing intelligence, Experiments, and Monitoring.
4. In Product health, explain D7 activation, WAU, retention, feature adoption,
   and CLV proxy.
5. In Pricing intelligence, show offer economics, guarded recommendations,
   scenario runs, and sensitivity checks.
6. In Experiments, explain why onboarding is a ship candidate and referral
   incentives need iteration on unit economics.
7. In Monitoring, show release-gate checks for marts, pricing, API readiness,
   batch scores, drift, and calibration.
8. Close with the technical spine: dbt marts, FastAPI contracts, tests, CI,
   model card, BigQuery/GCS loads, private Cloud Run API, scheduled Cloud Run
   jobs, and Cloud Monitoring alerts.

## Screenshot Checklist

Capture these after deploying or running locally:

- README first viewport with project title, live link, and dashboard screenshot.
- Streamlit Product health tab top metrics and first charts
  (`docs/assets/streamlit-product-health.png`).
- Streamlit Pricing intelligence tab with scenario runs and sensitivity checks.
- Streamlit Experiments tab with onboarding and referral readouts.
- Streamlit Monitoring tab showing release-gate status.
- Authenticated API `/health` smoke test or local API docs at `/docs`, showing
  scoring and pricing endpoints.
- Cloud Run Jobs or Cloud Monitoring page showing scheduled jobs and failure
  alerts.
- dbt docs lineage for mart models.
- GitHub Actions passing CI run.

## Final Pre-Post Checklist

- README links are current.
- Case study link is current.
- Streamlit deployment URL is live.
- GitHub repository description and topics are set.
- CI badge or latest GitHub Actions status is visible.
- Dashboard screenshots are current.
- LinkedIn post includes the GitHub URL and Streamlit URL.
- CV bullet is copied into the right version of the CV.
- Public wording says synthetic data only.
