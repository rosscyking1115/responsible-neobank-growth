# Customer Growth & Pricing Intelligence Platform

[![CI](https://github.com/rosscyking1115/neobank-product-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/rosscyking1115/neobank-product-analytics/actions/workflows/ci.yml)
[![Monitoring Snapshot](https://github.com/rosscyking1115/neobank-product-analytics/actions/workflows/monitoring-snapshot.yml/badge.svg)](https://github.com/rosscyking1115/neobank-product-analytics/actions/workflows/monitoring-snapshot.yml)

[Live Streamlit Dashboard](https://neobank-appuct-analytics.streamlit.app/)

![Neobank Product Analytics dashboard](docs/assets/streamlit-product-health.png)

## Executive Summary

Customer Growth & Pricing Intelligence Platform is a synthetic fintech data
product that connects customer analytics, experimentation, model decisioning,
pricing intelligence, and cloud deployment into one end-to-end workflow.

The project answers the kind of questions a product, growth, or customer
strategy team would ask in a neobank:

- Which customers activate, retain, and become higher-value users?
- Which onboarding treatment should be shipped, monitored, or iterated?
- Are referral incentives incrementally acquiring customers, or just subsidising
  signups that would have happened anyway?
- Which pricing or incentive offers are commercially attractive after guardrails?
- Can the scoring, monitoring, and API surfaces be operated as a small data
  product rather than a one-off notebook?

All data is synthetic. No customer data, internal bank data, or proprietary
business metrics are used.

## Delivered Product

- Public product dashboard for activation, engagement, retention, feature
  adoption, pricing, experiments, and monitoring.
- dbt metrics layer for product health, experiment readouts, pricing outcomes,
  and regional referral incrementality.
- Activation decisioning model with calibration, explainability, segment checks,
  and model card.
- Pricing intelligence workflow with offer economics, recommendation guardrails,
  scenario runs, and sensitivity analysis.
- Experimentation workflow covering CUPED A/B testing, SRM checks, guardrails,
  heterogeneous effects, DiD, synthetic control, and placebo checks.
- FastAPI service boundary for activation, churn, upsell, offer recommendation,
  and pricing scenario contracts.
- GCP path using Cloud Storage, BigQuery, Cloud Run, Cloud Scheduler, and Cloud
  Monitoring.
- Operations documentation for release checks, monitoring, score drift,
  realised-label calibration, rollback, and cost control.

## Business Outcomes

| Area | Output | Decision Value |
| --- | --- | --- |
| Activation | D7 activation model and onboarding A/B readout | Identify users needing onboarding help and decide whether to ship the treatment. |
| Retention | Post-activation retention and engagement views | Monitor whether activation quality translates into continued usage. |
| Pricing | Offer economics and scenario analysis | Compare margin, expected conversion, support risk, and fairness guardrails before rollout. |
| Referrals | Geo incrementality analysis | Estimate true lift and cost per incremental referred customer. |
| Monitoring | Release gates, drift checks, calibration, and alerts | Keep model and data outputs reviewable before operational use. |

## Production-Style Evidence

The portfolio version has been exercised beyond local development:

- Public Streamlit dashboard deployed on Streamlit Community Cloud.
- Cloud Storage raw landing path loaded into BigQuery.
- BigQuery raw tables verified against the export manifest.
- dbt graph run against BigQuery with 107 passing checks.
- Activation score extract loaded to `neobank_ml.customer_scores_daily`.
- BigQuery monitoring result written to `neobank_monitoring.score_monitoring_daily`.
- Private Cloud Run API deployed and smoke-tested via authenticated `/health`.
- Cloud Run Jobs deployed for activation scoring and score monitoring.
- Cloud Scheduler configured for daily scoring and monitoring runs.
- Cloud Monitoring alert policies created for Cloud Run job failures and API
  service errors.
- Budget alert and Cloud Storage lifecycle policy configured for cost control.

## Architecture

```text
Synthetic event generator
        |
        v
DuckDB / Parquet local development
        |
        +--> dbt marts --> Streamlit dashboard
        |
        +--> modelling and experiments --> model card, memos, monitoring
        |
        v
Cloud Storage raw landing
        |
        v
BigQuery raw tables and marts
        |
        +--> Cloud Run batch jobs --> scored users and monitoring table
        |
        +--> private Cloud Run API --> prediction and pricing contracts
        |
        v
Cloud Scheduler + Cloud Monitoring alerts
```

## Technology Stack

| Layer | Tools |
| --- | --- |
| Data generation | Python, Faker-style synthetic event generation, Parquet |
| Analytics engineering | dbt, DuckDB, BigQuery |
| Experimentation | CUPED, SRM checks, guardrails, DiD, synthetic control |
| Modelling | scikit-learn, calibration, explainability, model card |
| Application | Streamlit dashboard, FastAPI prediction service |
| Cloud | Google Cloud Storage, BigQuery, Cloud Run, Cloud Scheduler, Cloud Monitoring |
| Quality | pytest, ruff, GitHub Actions, monitoring snapshot workflow |

## Review Guide

For a five-minute review:

1. Open the [live dashboard](https://neobank-appuct-analytics.streamlit.app/).
2. Review product health, pricing intelligence, experiments, and monitoring.
3. Skim the architecture in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
4. Read the API contract in [docs/API.md](docs/API.md).
5. Review the model card in
   [docs/model_cards/MODEL_ACTIVATION_DECISIONING.md](docs/model_cards/MODEL_ACTIVATION_DECISIONING.md).
6. Review the runbook in [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md).

## Key Documentation

| Document | Purpose |
| --- | --- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Local and cloud architecture overview. |
| [docs/API.md](docs/API.md) | Prediction and pricing scenario API contract. |
| [docs/CLOUD_RUN_DEPLOYMENT.md](docs/CLOUD_RUN_DEPLOYMENT.md) | Private Cloud Run API and job deployment evidence. |
| [docs/GCP_WAREHOUSE.md](docs/GCP_WAREHOUSE.md) | Cloud Storage and BigQuery warehouse path. |
| [docs/MONITORING.md](docs/MONITORING.md) | Data, model, score, and GCP monitoring checks. |
| [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md) | Rollback triggers, triage, and GCP operations. |
| [docs/PRICING_SCENARIOS.md](docs/PRICING_SCENARIOS.md) | Pricing recommendation and scenario framework. |
| [docs/PUBLIC_LAUNCH.md](docs/PUBLIC_LAUNCH.md) | Portfolio, LinkedIn, and CV wording. |

## Local Reproduction

The project is reproducible without GCP. The local path builds a synthetic
dataset, dbt marts, tests, and the dashboard.

```powershell
uv sync --group dev
uv run python -m data_generator.generate --users 5000 --months 6 --output-dir raw/ci
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank
uv run pytest
uv run streamlit run app/streamlit_app.py
```

For the full portfolio-size data run, use:

```powershell
uv run python -m data_generator.generate --users 50000 --months 12 --output-dir raw/portfolio_full
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank --vars "{raw_path: raw/portfolio_full}"
```

## Public Release Notes

This is a synthetic portfolio case study inspired by public fintech product
analytics themes. It is designed to show how product analysis, causal inference,
pricing analytics, model decisioning, and cloud operations can be combined into a
small but credible data product.

The project should not be interpreted as representing any real financial
institution. It uses no real customer data.

## What Would Be Hardened For Production

A real regulated-financial-services deployment would add:

- Stronger API protection through API Gateway, IAP, JWT, or service-to-service
  IAM, plus rate limits and structured request logging.
- Formal data governance with row-level and column-level controls, retention
  policy, ownership, lineage, query labels, and cost controls.
- Keyless CI/CD deployment through GitHub OIDC, container vulnerability scanning,
  SBOMs, and infrastructure as code.
- A model registry or feature store for reproducible training, shadow
  deployments, and online/offline feature parity.
- Formal privacy, Consumer Duty, model-risk, audit, and approval controls before
  any live customer decisioning.
