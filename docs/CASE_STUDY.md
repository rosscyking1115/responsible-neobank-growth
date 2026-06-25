# Case Study: Customer Growth & Pricing Intelligence Platform

## Context

This project is a synthetic fintech data product for a neobank growth, product,
or customer strategy team. It brings together customer behaviour analytics,
experimentation, pricing decisions, model decisioning, and cloud operations into
one reproducible workflow.

The product is designed around a realistic operating question:

> How should a fintech team decide which activation, referral, and pricing
> interventions to scale while protecting customer experience and business
> economics?

All data is synthetic. No real customer, bank, or proprietary business data is
used.

## Users

The intended users are:

- Product managers reviewing activation, retention, and feature adoption.
- Growth analysts measuring onboarding and referral incrementality.
- Pricing or commercial teams comparing offer economics and guardrails.
- Data scientists monitoring activation decisioning and score quality.
- Analytics engineers maintaining reproducible marts and data quality checks.

## Product Decisions Supported

| Decision Area | Question | Output |
| --- | --- | --- |
| Activation | Which users need onboarding support? | D7 activation model, segment checks, and onboarding experiment readout. |
| Retention | Is activation translating into continued usage? | Weekly engagement, retention, feature adoption, and CLV proxy views. |
| Referrals | Are incentives creating incremental customers? | DiD, synthetic-control, placebo, and cost-per-incremental-user readout. |
| Pricing | Which offers should scale, test, or pause? | Offer margin, recommendation guardrails, scenario runs, and sensitivity analysis. |
| Operations | Is the data product safe to refresh or demo? | Monitoring checks for data freshness, model artifacts, calibration, drift, and cloud readiness. |

## What Was Built

- Synthetic customer event generator for users, sessions, transactions,
  referrals, support contacts, product features, experiments, and pricing
  exposures.
- dbt warehouse with staging, intermediate, product, finance, experiment, geo,
  and pricing marts.
- Experimentation layer covering CUPED A/B testing, SRM checks, guardrails,
  heterogeneous effects, DiD, synthetic control, and placebo checks.
- Activation decisioning model with calibration, explainability, batch scoring,
  monitoring reports, and a model card.
- Pricing intelligence workflow with offer economics, guarded recommendations,
  scenario runs, and sensitivity analysis.
- Public Streamlit dashboard and private FastAPI service boundary.
- GCP path using Cloud Storage, BigQuery, Cloud Run, Cloud Scheduler, and Cloud
  Monitoring.

## Evidence Of Product Readiness

The project has been exercised beyond a local notebook workflow:

- Streamlit dashboard deployed publicly.
- Raw Parquet export uploaded to Cloud Storage and loaded into BigQuery.
- BigQuery raw tables verified against the export manifest.
- dbt models run against the BigQuery path.
- Activation score extract loaded to BigQuery.
- Score monitoring result written to a monitoring dataset.
- Cloud Run API deployed privately and smoke-tested.
- Cloud Run Jobs deployed for scoring and monitoring.
- Cloud Scheduler configured for daily batch runs.
- Cloud Monitoring alert policies configured for API and job failures.
- CI covers linting, tests, notebook checks, dbt build, and container builds.

## Method Choices

The project favours transparent, reviewable methods over opaque demos:

- CUPED is used where pre-treatment signal can reduce variance.
- Geo incrementality is triangulated with DiD and synthetic control rather than
  relying on raw before-after comparisons.
- Pricing recommendations include guardrails for margin, complaint rate,
  support load, and human review exposure.
- Model output includes calibration, explainability, segment checks, and
  monitoring before operational use.

## Limitations

This is a portfolio case study, not a production banking system. A live
regulated deployment would require stronger identity and access controls,
formal data governance, privacy review, audit approvals, model-risk governance,
consumer-outcome monitoring, infrastructure as code, and a managed feature/model
registry.

## Result

The finished project demonstrates an end-to-end data product rather than a
single analysis: reproducible data generation, trusted marts, causal decision
readouts, ML decisioning, pricing scenario simulation, public dashboarding,
API contracts, cloud batch jobs, monitoring, and operational documentation.
