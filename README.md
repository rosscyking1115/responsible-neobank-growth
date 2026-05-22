# Neobank Product Analytics

A Monzo-inspired product analytics portfolio project using dbt, DuckDB, Python,
experimentation, and synthetic-control geo lift analysis.

## How to Read This Repo in 5 Minutes

1. Start with the two decision memos in `docs/memos/` once the experiments land.
2. Check the dbt models in `dbt_neobank/models/` for the trusted metrics layer.
3. Open the Marimo notebooks in `notebooks/` for analysis narratives.
4. Run the Streamlit dashboard in `app/streamlit_app.py` for the PM-facing view.

## Why This Exists

This project simulates a neobank product analytics workflow on a stack that mirrors
how a modern fintech data team works: warehouse-backed metrics, dbt transformations,
Python modelling, experimentation, and decision memos that a product manager could
act on.

The project is aimed at a Product Data Scientist role with a Growth/Marketing accent.
It keeps activation, retention, primary-bank engagement, and customer lifetime value
central, while using a regional referral incrementality chapter to show causal
thinking around network effects.

## Current Monzo-Aligned Signals

The plan is refreshed against Monzo's public 2026 direction:

- Product analytics in embedded squads: metrics, experimentation, targeting models,
  ambiguity, and communication.
- Data platform expectations: dbt, governed data products, ownership, model
  interfaces, freshness, and CI checks.
- Business priorities: primary banking, word-of-mouth growth, business banking,
  borrowing, wealth, safety, and responsible machine learning.
- Fintech standards: Consumer Duty guardrails, vulnerable-customer checks, model
  explainability, exposure logging, sample-ratio checks, and rollout monitoring.

## Planned Deliverables

- Synthetic neobank event data for users, transactions, sessions, features,
  referrals, support contacts, and experiments.
- dbt metrics layer with activation, retention, engagement, feature adoption, CLV
  proxy, experiment user metrics, and geo daily signups.
- Marimo notebooks for EDA, A/B testing with CUPED, activation decisioning, and
  regional referral incrementality.
- Calibrated activation model with explainability and customer-outcome guardrails.
- Streamlit dashboard for product metrics and experiment readouts.
- One-page decision memos for the A/B onboarding test and referral geo experiment.

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

## Generate Synthetic Data

```powershell
uv run python -m data_generator.generate --users 50000 --months 12 --output-dir raw/phase1_full
```

The generator writes parquet files for users, experiment assignments, activation
ground truth, transactions, sessions, feature events, support contacts, referrals,
regional daily signups, and embedded experiment ground truth. The `raw/` directory
is gitignored so the data is reproducible without committing generated artifacts.

## Phase Status

- Phase 0: setup and scaffolding complete.
- Phase 1: synthetic data generator complete.
- Phase 2: dbt metrics layer complete.
- Phase 3: EDA product insights complete.
- Phase 4: A/B experimentation pending.
- Phase 5: activation decisioning model pending.
- Phase 6: regional referral experiment pending.
- Phase 7: dashboard and memos pending.
- Phase 8: polish and public release pending.

The repository should remain private through Phase 0 and flip public once the
synthetic data generator is merged and reproducible.
