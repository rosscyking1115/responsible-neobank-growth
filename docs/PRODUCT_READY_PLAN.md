# Product-Ready Upgrade Plan

Target public title: **Customer Growth & Pricing Intelligence Platform**

Research date: 2026-05-29

## Recommendation

Upgrade this repo from a synthetic neobank analytics case study into a small
industrial data product: a governed customer growth and pricing intelligence
platform with a cloud warehouse path, prediction APIs, batch scoring, monitoring,
and product-grade documentation.

The strongest story is no longer "I made a dashboard." It is: "I built a
reproducible customer intelligence platform that connects data modelling,
experimentation, ML decisioning, pricing economics, and monitored deployment."

## Current Baseline

Already strong:

- Synthetic event generator for users, transactions, sessions, feature events,
  support contacts, referrals, experiment assignments, and regional signups.
- dbt DuckDB warehouse with activation, retention, engagement, feature adoption,
  CLV proxy, experiment, and geo incrementality marts.
- Streamlit product dashboard for product health and experiment readouts.
- Activation modelling with calibration, explainability, and guardrail checks.
- FastAPI service boundary for activation, churn, upsell, offer recommendation,
  and pricing scenario contracts.
- Activation model artifact registry with persisted metadata, threshold, feature
  schema, training window, metrics, and model-card linkage.
- Local daily activation batch scorer that writes a partitioned
  `customer_scores_daily` extract.
- Pricing-domain foundation with synthetic offer catalogue, incentive exposures,
  acceptance outcomes, margin assumptions, and guardrail recommendation marts.
- Onboarding A/B and referral geo analyses with causal inference and memos.
- CI for linting, notebooks, tests, data generation, and dbt build.
- Model card and public-release notes.

Main product-readiness gaps:

- Pricing scenario simulation is still API-only logic; it is not yet connected to
  the new pricing marts or shown in the dashboard.
- No BigQuery or Cloud Storage path; the warehouse is local DuckDB only.
- Batch scoring is local only; it still needs scheduling, scoring logs, cloud
  storage/warehouse loading, and rollback documentation.
- No monitoring layer beyond tests: source freshness, drift, calibration,
  scoring distribution, API health, and operational runbook are missing.
- No container, deployment gate, or Cloud Run job/service workflow.

## Target Product

The finished product should have three surfaces:

1. Product dashboard
   - Streamlit remains the public executive/product readout.
   - It should show growth, activation, retention, pricing economics,
     experiments, and monitoring status.

2. Prediction and scenario API
   - FastAPI service deployed locally first, then Cloud Run ready.
   - Endpoints:
     - `GET /health`
     - `POST /score/activation`
     - `POST /score/churn`
     - `POST /score/upsell`
     - `POST /recommend/offer`
     - `POST /simulate/pricing`

3. Batch scoring and monitoring outputs
   - Scheduled batch scoring writes `customer_scores_daily`.
   - Monitoring writes data quality, freshness, model performance, calibration,
     drift, and guardrail reports.

## Target Architecture

```text
Synthetic source events
  -> local parquet and optional Cloud Storage raw zone
  -> BigQuery raw datasets or local DuckDB
  -> dbt staging, intermediate, mart, and ml_features layers
  -> customer 360, experiment, pricing, and monitoring marts
  -> Python / BigQuery ML training and batch scoring
  -> FastAPI prediction and pricing scenario service
  -> Streamlit product dashboard
  -> CI, data quality checks, model monitoring, and operational docs
```

Cloud target:

- Cloud Storage raw buckets for parquet landing data.
- BigQuery datasets: `raw`, `staging`, `intermediate`, `mart_growth`,
  `mart_pricing`, `mart_experiments`, `ml_features`, and `monitoring`.
- dbt targets for local DuckDB and BigQuery.
- Cloud Run service for the API.
- Cloud Run jobs for batch scoring, data quality, and monitoring reports.
- GitHub Actions gates for tests, dbt build, API contract tests, and container
  smoke checks.

## Workstreams

### 1. Product Framing

Deliverables:

- Rename the public project positioning to Customer Growth & Pricing Intelligence
  Platform while keeping the synthetic neobank context explicit.
- Add an architecture diagram and product scope document.
- Add a data dictionary and glossary for activation, retention, CLV proxy,
  referral incrementality, pricing economics, churn, upsell, and guardrails.

Acceptance criteria:

- README tells a recruiter what the product does in under 30 seconds.
- Docs clearly state that all data is synthetic.
- The project can be described as a data product, not only analysis.

### 2. Pricing Intelligence Domain

Deliverables:

- Extend synthetic data with:
  - offer catalogue
  - pricing and incentive exposures
  - customer eligibility flags
  - product margin assumptions
  - simulated plan, savings, or incentive adoption outcomes
- Add dbt marts:
  - `fct_offer_exposures`
  - `fct_pricing_outcomes`
  - `fct_customer_value_daily`
  - `mart_pricing_recommendations`
- Add scenario logic for incentive, fee, or offer changes by segment.

Acceptance criteria:

- Pricing recommendations include expected activation or upsell lift, expected
  margin, support/contact guardrails, vulnerable-customer checks, and reason
  codes.
- The project avoids unsafe claims about regulated credit decisions or real
  personalised pricing.

### 3. BigQuery Warehouse Readiness

Deliverables:

- Add `dbt-bigquery` dependency path and BigQuery profile documentation.
- Keep DuckDB as the default local target.
- Add BigQuery-compatible SQL fixes where needed.
- Add partitioning and clustering configs for high-volume fact tables.
- Add source freshness and public mart contracts for downstream consumers.

Acceptance criteria:

- `dbt build` still works locally on DuckDB.
- BigQuery target is documented with environment variables, dataset names, and
  service account assumptions.
- Public marts have data tests for uniqueness, not-null, accepted values,
  relationships, non-negative economics, and no post-treatment leakage.

### 4. Prediction API

Deliverables:

- Add FastAPI app under `api/`.
- Add Pydantic request and response schemas for activation, churn, upsell, offer
  recommendation, and pricing scenario simulation.
- Add OpenAPI examples and `docs/API.md`.
- Add pytest API tests.

Acceptance criteria:

- Local API starts with one command.
- `/health` returns model version, data version, and service status.
- Prediction endpoints return calibrated probabilities, decision thresholds,
  reason codes, and guardrail flags.
- Contract tests fail when schemas change unexpectedly.

### 5. Model Packaging And Scoring

Deliverables:

- Persist trained artifacts under an ignored `artifacts/` path.
- Save feature schema, training window, data hash, metrics, thresholds, and model
  card metadata.
- Add batch scoring command that writes `customer_scores_daily`.
- Add a simple registry file for model versions and active model alias.

Acceptance criteria:

- Training, evaluation, and batch scoring are reproducible from commands.
- API and batch scorer use the same feature contract.
- Model card updates can be generated from the latest evaluation.

### 6. Monitoring And Governance

Deliverables:

- Add monitoring reports for:
  - dbt data quality failures
  - source freshness
  - feature drift and prediction distribution drift
  - calibration by segment
  - score coverage and null-rate checks
  - pricing guardrail violations
  - support, complaint, and vulnerable-customer outcomes
- Add `docs/MONITORING.md` and an operational runbook.

Acceptance criteria:

- A single command can generate a monitoring snapshot.
- Dashboard can show a compact monitoring summary.
- Reports explain what would trigger a rollback or human review.

### 7. Cloud Run Deployment

Deliverables:

- Add Dockerfile for API service.
- Add Cloud Run deployment notes for API and jobs.
- Add environment-variable based config for local, Streamlit, and GCP modes.
- Add optional GitHub Actions workflow for container build smoke tests.

Acceptance criteria:

- API container builds locally.
- Container smoke test hits `/health`.
- Deployment docs cover service account, BigQuery access, secrets, and rollback.

### 8. Final Public Release

Deliverables:

- Updated README and release notes for LinkedIn/CV.
- Architecture diagram screenshot.
- Streamlit screenshots.
- API docs screenshot.
- dbt lineage screenshot.
- CI badge and passing release checklist.

Acceptance criteria:

- Public story is concise: growth analytics, pricing intelligence,
  experimentation, ML decisioning, GCP data product.
- Repo can be reviewed without private credentials.
- Any cloud-specific step has a local fallback.

## Build Order

Recommended first build sequence:

1. Product framing docs, architecture diagram, and README positioning.
2. FastAPI skeleton with health endpoint, schemas, tests, and Dockerfile.
3. Existing activation model packaged as the first served model.
4. Batch scoring and model registry metadata.
5. Pricing synthetic data and pricing marts.
6. Pricing scenario endpoint and dashboard section.
7. BigQuery target documentation and Cloud Storage landing pattern.
8. Monitoring reports and dashboard monitoring summary.
9. Cloud Run deployment docs and container smoke test workflow.

This order gives the fastest visible jump from portfolio project to product
platform: API first, then model serving, then pricing, then cloud hardening.

## Research Basis

The plan follows current public platform guidance as of 2026-05-29:

- Google Cloud describes Cloud Run as a fully managed platform for services,
  jobs, and worker pools, with HTTPS services suitable for APIs and jobs suitable
  for scheduled batch workloads:
  <https://cloud.google.com/run/docs/overview/what-is-cloud-run>
- BigQuery supports loading Parquet and other formats from Cloud Storage as
  batch operations:
  <https://cloud.google.com/bigquery/docs/loading-data-cloud-storage>
- BigQuery partitioning and clustering are the right primitives for fact-table
  cost and performance management:
  <https://cloud.google.com/bigquery/docs/partitioned-tables>
- BigQuery ML supports SQL-based model training and prediction, plus imported
  models for in-warehouse inference:
  <https://cloud.google.com/bigquery/docs/bqml-introduction>
  <https://cloud.google.com/bigquery/docs/inference-overview>
- Vertex AI model monitoring supports feature skew and drift detection for
  deployed models:
  <https://cloud.google.com/vertex-ai/docs/model-monitoring/using-model-monitoring>
- Cloud Storage lifecycle management supports TTL, object retention, and storage
  class management:
  <https://cloud.google.com/storage/docs/lifecycle>
- dbt data tests, sources, source freshness, exposures, and model contracts are
  the relevant governance features for trusted downstream marts:
  <https://docs.getdbt.com/docs/build/data-tests>
  <https://docs.getdbt.com/docs/build/sources>
  <https://docs.getdbt.com/docs/build/exposures>
  <https://docs.getdbt.com/docs/mesh/govern/model-contracts>
