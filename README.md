# Customer Growth & Pricing Intelligence Platform

A synthetic neobank product analytics case study using dbt, DuckDB, Python,
experimentation, activation modelling, and geo-lift analysis.

This repo simulates the end-to-end workflow of a Product Data Scientist working
in a modern fintech squad: generate realistic event data, build trusted metrics,
analyse product experiments, document model guardrails, and translate the work
into PM-ready dashboard and decision outputs.

The next product-ready upgrade path is documented in
`docs/PRODUCT_READY_PLAN.md`. It reframes the project as a cloud-ready customer
growth and pricing intelligence platform with prediction APIs, BigQuery/dbt
readiness, batch scoring, monitoring, and deployment gates.

## How to Review This Repo

1. Start with the decision memos in `docs/memos/`.
2. Open the Streamlit dashboard in `app/streamlit_app.py` for the product view.
3. Check the dbt models in `dbt_neobank/models/` for the trusted metrics layer.
4. Read the activation model card in `docs/model_cards/`.
5. Open the Marimo notebooks in `notebooks/` for the analytical narrative.

## Portfolio Highlights

- Built a reproducible synthetic neobank warehouse covering users, transactions,
  sessions, feature events, referrals, support contacts, and experiments.
- Modelled activation, retention, engagement, feature adoption, CLV proxy,
  experiment metrics, and region-day referral incrementality in dbt.
- Analysed a personalised onboarding A/B test with SRM, CUPED, guardrails, power,
  heterogeneous effects, and a launch recommendation.
- Trained and documented an activation decisioning model with calibration,
  explainability, fairness-oriented segment checks, and customer-outcome guardrails.
- Estimated regional referral incrementality using DiD, synthetic control,
  spillover checks, placebos, and embedded ground-truth recovery.
- Delivered a Streamlit dashboard and decision memos designed for product review.

## Why This Exists

This project simulates a neobank product analytics workflow on a stack that mirrors
how a modern fintech data team works: warehouse-backed metrics, dbt transformations,
Python modelling, experimentation, and decision memos that a product manager could
act on.

The project is aimed at a Product Data Scientist role with a Growth/Marketing accent.
It keeps activation, retention, primary-bank engagement, and customer lifetime value
central, while using a regional referral incrementality chapter to show causal
thinking around network effects.

## Fintech Product Analytics Themes

The case study is designed around public fintech product analytics themes:

- Product analytics in embedded squads: metrics, experimentation, targeting models,
  ambiguity, and communication.
- Data platform expectations: dbt, governed data products, ownership, model
  interfaces, freshness, and CI checks.
- Business priorities: primary banking, word-of-mouth growth, business banking,
  borrowing, wealth, safety, and responsible machine learning.
- Fintech standards: Consumer Duty guardrails, vulnerable-customer checks, model
  explainability, exposure logging, sample-ratio checks, and rollout monitoring.

## Deliverables

- Synthetic neobank event data for users, transactions, sessions, features,
  referrals, support contacts, and experiments.
- dbt metrics layer with activation, retention, engagement, feature adoption, CLV
  proxy, experiment user metrics, pricing outcomes, and geo daily signups.
- Marimo notebooks for EDA, A/B testing with CUPED, activation decisioning, and
  regional referral incrementality.
- Calibrated activation model with explainability and customer-outcome guardrails.
- Pricing intelligence marts with offer exposure, unit economics, and guardrail
  recommendation reason codes.
- Streamlit dashboard for product metrics, pricing intelligence, and experiment
  readouts.
- One-page decision memos for the A/B onboarding test and referral geo experiment.
- Portfolio release notes with CV and LinkedIn wording in `docs/PORTFOLIO_RELEASE.md`.

## Core Metrics

- D7 activation: first card transaction within 7 days of signup.
- W4 retention: activated users transacting in week 4.
- Feature adoption: Savings Pots, Salary Sorter, referrals, and related product use.
- WAU and transaction frequency.
- CLV proxy: simulated 12-month net revenue per user.
- Guardrails: support contact rate, complaint/contact load, fraud flags, crash rate,
  vulnerable-customer impact, and fair-value/customer-understanding signals.

## Local Setup

```powershell
uv sync --group dev
uv run python -m data_generator.generate --users 5000 --months 6 --output-dir raw/ci
uv run pytest
uv run ruff check .
uv run marimo check notebooks --ignore-scripts
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank
```

## dbt Documentation

```powershell
uv run dbt docs generate --project-dir dbt_neobank --profiles-dir dbt_neobank
uv run dbt docs serve --project-dir dbt_neobank --profiles-dir dbt_neobank
```

## Run the Prediction API

```powershell
uv run uvicorn api.main:app --reload --port 8000
```

The API exposes activation, churn, upsell, offer recommendation, and pricing
scenario contracts. See `docs/API.md` for request examples and guardrail fields.

For the API container and Cloud Run path, see `docs/CLOUD_RUN_DEPLOYMENT.md`.

## Generate Synthetic Data

```powershell
uv run python -m data_generator.generate --users 50000 --months 12 --output-dir raw/portfolio_full
```

The generator writes parquet files for users, experiment assignments, activation
ground truth, transactions, sessions, feature events, support contacts, referrals,
regional daily signups, and embedded experiment ground truth. The `raw/` directory
is gitignored so the data is reproducible without committing generated artifacts.

## Reproduce the Onboarding A/B Memo

```powershell
uv run python -m data_generator.generate --users 50000 --months 12 --output-dir raw/portfolio_full
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank --vars "{raw_path: raw/portfolio_full}"
uv run python -m src.experiments.run_onboarding_ab
```

## Reproduce the Activation Model Card

```powershell
uv run python -m data_generator.generate --users 50000 --months 12 --output-dir raw/portfolio_full
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank --vars "{raw_path: raw/portfolio_full}"
uv run python -m src.modelling.run_activation_model
```

The model command writes the model card plus an ignored local artifact registry at
`artifacts/models/activation/registry.json`. Set
`NEOBANK_ACTIVATION_MODEL_REGISTRY` to that file when serving model-backed
activation scores from the API.

## Reproduce Batch Activation Scores

```powershell
uv run python -m src.modelling.run_activation_model
uv run python -m src.modelling.batch_score_activation --score-date 2025-06-30
```

The batch scorer writes an ignored daily parquet extract under
`artifacts/scoring/activation/`. See `docs/BATCH_SCORING.md` for the output
contract.

## Generate a Monitoring Snapshot

```powershell
uv run python -m src.monitoring.snapshot --snapshot-date 2025-06-30
uv run python -m src.monitoring.model_report --report-date 2025-06-30
```

The monitoring commands write JSON and Markdown reports under
`artifacts/monitoring/` with data quality, activation, experiment, pricing,
batch-scoring, API-readiness, score-distribution, and drift checks. See
`docs/MONITORING.md`.

## Render the GCP Warehouse Load Plan

```powershell
uv run python -m src.cloud.gcp_load_plan
```

The load plan turns the tracked Cloud Storage/BigQuery manifest into `bq load`
commands for the raw parquet warehouse landing layer. See `docs/GCP_WAREHOUSE.md`.

## Reproduce Pricing Intelligence Marts

```powershell
uv run python -m data_generator.generate --users 50000 --months 12 --output-dir raw/portfolio_full
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank --vars "{raw_path: raw/portfolio_full}" --select marts/pricing
```

The pricing marts model synthetic offer exposures, acceptance, incentive cost,
30-day margin, support/complaint guardrails, and recommendation reason codes.

## Reproduce the Referral Geo Memo

```powershell
uv run python -m data_generator.generate --users 50000 --months 12 --output-dir raw/portfolio_full
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank --vars "{raw_path: raw/portfolio_full}"
uv run python -m src.experiments.run_referral_incrementality
```

## Run the Product Dashboard

```powershell
uv run python -m data_generator.generate --users 50000 --months 12 --output-dir raw/portfolio_full
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank --vars "{raw_path: raw/portfolio_full}"
uv run streamlit run app/streamlit_app.py
```

The dashboard reads the dbt marts in `neobank.duckdb` and displays product health,
pricing intelligence, onboarding A/B results, and referral geo incrementality.
If `neobank.duckdb` does not exist, the dashboard automatically generates a
5,000-user synthetic demo dataset and builds the dbt marts on first load.

For a lightweight CI-sized run, use the default `raw/ci` data generated in Local
Setup. For portfolio screenshots, use the 50,000-user commands above.

## Deploy on Streamlit Community Cloud

Use `app/streamlit_app.py` as the app entrypoint and `requirements.txt` for
dependencies. No secrets are required. See `docs/STREAMLIT_DEPLOYMENT.md` for the
full deployment checklist and cold-start behavior.

## Public Release Notes

This repo uses synthetic data only. No Monzo internal data, customer data, or
proprietary business metrics are included. The Monzo references are public-context
inspiration for a realistic fintech product analytics workflow.
