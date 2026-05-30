# Product-Ready Upgrade Plan

Target public title: **Customer Growth & Pricing Intelligence Platform**

Original research date: 2026-05-29

Standards refresh: 2026-05-30

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
- Local monitoring snapshot command for DuckDB mart availability, activation,
  experiment, pricing, batch-score, and API readiness checks.
- Streamlit monitoring tab for operational status counts, attention items, and
  the full check table.
- Activation model monitoring report for score distribution, PSI drift,
  targeting rate, and vulnerable-customer review load.
- Weekly/manual GitHub Actions monitoring snapshot workflow with downloadable
  report artifacts for product, model, and API checks.
- GCP raw warehouse load manifest with BigQuery `bq load` command rendering,
  Cloud Storage path conventions, a raw row-count verification plan, and a
  BigQuery dbt target.
- Small demo raw landing path exercised against GCS and BigQuery on 2026-05-30:
  13 parquet files uploaded, 13 raw tables loaded, and all manifest row counts
  verified in BigQuery.
- dbt graph exercised against BigQuery on 2026-05-30: staging views,
  intermediate tables, mart tables, and 107 dbt tests passed.
- Cloud Run-compatible API container with CI build and `/health` smoke test.
- Onboarding A/B and referral geo analyses with causal inference and memos.
- CI for linting, notebooks, tests, data generation, and dbt build.
- Model card and public-release notes.

Main product-readiness gaps:

- Pricing scenario simulation is backed by the recommendation mart, but still
  needs cloud persistence and production-style audit history.
- BigQuery and Cloud Storage now have an exercised demo raw-load path and dbt
  mart build; BigQuery governance, cost controls, and scheduled execution still
  need hardening.
- Batch scoring is local only; it still needs a BigQuery write path, scoring
  logs, cloud storage/warehouse loading, and rollback documentation.
- Monitoring is local snapshot-based with dashboard surfacing, score-drift
  reporting, realised-label calibration monitoring, a weekly GitHub Actions
  artifact, and an operational runbook; scheduled cloud execution and alert
  routing remain future work.
- Cloud Run service deployment is documented and container-gated in CI; Cloud Run
  jobs for batch scoring and monitoring, private ingress, production auth, and
  Secret Manager integration remain future work.

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

## GCP Upgrade Kit Alignment

`NEOBANK_GCP_UPGRADE_KIT.md` is now part of the delivery plan. Treat it as the
handoff document for turning the current public Streamlit demo into a
production-style GCP portfolio project.

Important distinction:

- The Streamlit dashboard is already publicly deployed.
- The API is Cloud Run compatible and container-tested.
- The raw warehouse landing layer and dbt mart layer are **GCP-exercised** for
  the demo export. Batch scoring, monitoring jobs, and cloud security hardening
  are still **GCP-ready**, not yet fully **GCP-deployed**.
- Do not claim Vertex AI or full GCP deployment unless those resources are
  actually created and exercised.

The kit changes the next phase from "add more analysis" to "prove a cloud data
product path":

- Add local/GCP configuration and `.env.example` without committing secrets.
- Export synthetic data into cloud-ready files with a manifest.
- Upload raw files to Cloud Storage and load BigQuery raw tables.
- Run dbt against BigQuery while keeping DuckDB as the default local path.
- Write propensity or activation scores back to BigQuery.
- Harden Cloud Run deployment so production guidance is private-by-default.
- Keep monitoring lightweight, reproducible, and evidence-based.

## Reassessed Roadmap

Immediate next build session:

1. Cloud configuration and security skeleton
   - Add `.env.example` for `NEOBANK_ENV`, GCP project, region, bucket,
     BigQuery dataset, and credential path placeholders.
   - Add a typed config helper for local and GCP modes.
   - Document local mode vs GCP mode and the rule that secrets stay outside git.

2. Cloud export vertical slice
   - Add a deterministic export command for generated synthetic data.
   - Write cloud-ready files to an ignored export directory.
   - Produce a manifest with row counts, schema version, generation config, and
     run timestamp.
   - Add tests for expected files and nonzero row counts.

3. GCS and BigQuery raw-load path
   - Done for the demo path: generated parquet, uploaded to GCS, loaded 13 raw
     tables into BigQuery, and verified row counts.
   - Cost-control follow-up: render inventory, lifecycle, and scoped cleanup
     commands for the demo GCS prefix and raw BigQuery dataset.
   - dbt BigQuery marts: done for the demo path with 107 passing dbt checks.

Near-term hardening:

4. dbt governance
   - Add formal dbt `sources`, source freshness, exposures for Streamlit/API
     consumers, owners/meta, and contracts for public marts.

5. BigQuery governance
   - Add an IAM matrix, table/dataset naming policy, query labels, maximum bytes
     billed guidance, partitioning/clustering checks, and examples for row-level
     or column-level controls where customer-sensitive fields would exist.

6. Cloud Run and API security
   - Make deployment docs private-by-default.
   - Use a dedicated runtime service account, Secret Manager, restricted
     ingress, explicit CORS, request IDs, structured logs, and a documented
     auth option such as API key, IAP, API Gateway, or JWT.

7. Supply-chain and CI controls
   - Add least-privilege workflow permissions, Dependabot, dependency review or
     equivalent scanning, and container vulnerability/SBOM guidance.

Future phases:

- Cloud Run jobs for batch scoring and monitoring snapshots.
- GitHub OIDC to GCP for keyless deployment.
- Cloud Monitoring alert examples and SLO notes.
- Vertex AI only if it adds clear value beyond the current scikit-learn and
  BigQuery path.
- Terraform only after the manual GCP path is stable and worth codifying.

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
6. Pricing scenario endpoint, persisted scenario runs, and dashboard section.
7. BigQuery target documentation and Cloud Storage landing pattern. Done as a
   local manifest and command renderer; live cloud execution remains optional.
8. Monitoring dashboard summary, drift checks, and operational runbook. Done for
   local snapshots, dashboard surfacing, score drift, realised-label calibration,
   and release triage; scheduled cloud jobs remain future work.
9. Cloud Run deployment docs and container smoke test workflow. Done for the API
   service; batch and monitoring jobs remain future work.

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
- The 2026-05-30 standards refresh adds explicit security and governance
  priorities from Google Cloud, OWASP, NIST, GitHub, FastAPI, and Streamlit:
  <https://docs.cloud.google.com/architecture/framework/security>
  <https://docs.cloud.google.com/run/docs/securing/security>
  <https://docs.cloud.google.com/bigquery/docs/access-control-intro>
  <https://owasp.org/API-Security/editions/2023/en/0x10-api-security-risks/>
  <https://csrc.nist.gov/pubs/sp/800/218/final>
  <https://www.nist.gov/publications/nist-cybersecurity-framework-csf-20>
  <https://docs.github.com/en/actions/concepts/security/openid-connect>
  <https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/>
  <https://docs.streamlit.io/develop/concepts/connections/secrets-management>
