# Neobank GCP Upgrade Kit

Use this file as handoff context for upgrading the existing `neobank-product-analytics` project into a product-ready cloud/data-science portfolio project.

## Goal

Upgrade the current local neobank product analytics project into a small but credible cloud-deployed data product:

**Customer Growth & Pricing ML Platform on GCP**

The final project should prove that Ross can move beyond local analysis into a production-style workflow using cloud storage, a cloud warehouse, batch scoring, a deployed API or dashboard, tests, documentation, and business-facing outputs.

This upgrade is higher value than an entry-level cloud certificate because job posts repeatedly ask for:

- GCP / BigQuery / cloud warehouse experience
- production-style deployment
- APIs or batch scoring
- orchestration or repeatable pipelines
- model monitoring / drift checks
- MLOps basics
- stakeholder-facing business impact

## Candidate Context

Ross is applying for UK data scientist / applied scientist / product analytics roles such as:

- ASOS Applied Scientist, Customer & Marketing ML
- Trustpilot Data Scientist, GTM Applied AI / Pricing
- Lendable Data Scientist, UK Cards
- Guardian Data Scientist
- Ipsos Data Scientist, Brand Health Tracking

The strongest existing project is `neobank-product-analytics`, which already demonstrates:

- synthetic fintech customer-event generation
- activation, retention, feature adoption, CLV proxy
- onboarding A/B testing with CUPED and guardrails
- referral incrementality with difference-in-differences and synthetic control
- dbt + DuckDB analytics layer
- Streamlit dashboard
- decision memos and model card style documentation

The missing signal is not more modelling. The missing signal is:

> I can deploy a data/model product into a cloud/production-style environment.

## Target CV Bullet

After completion, Ross should be able to put this on his CV:

```text
Built a GCP-deployed customer growth ML platform using BigQuery, Cloud Storage, Cloud Run, Python, SQL/dbt and scikit-learn, modelling activation, retention, CLV and upsell propensity from customer-level event data with reproducible tests and business-facing dashboards.
```

If Vertex AI is included:

```text
Deployed a customer propensity modelling workflow on GCP using BigQuery, Cloud Storage, Vertex AI and Cloud Run, with reproducible data preparation, model evaluation, batch scoring and business-facing decision outputs.
```

## Recommended Architecture

Minimum credible cloud architecture:

```text
Synthetic data generator
        |
        v
Local CSV/Parquet export
        |
        v
Google Cloud Storage bucket
        |
        v
BigQuery raw tables
        |
        v
dbt models in BigQuery
        |
        +--> analytics marts: activation, retention, CLV, referrals, experiments
        |
        v
Python model training / scoring
        |
        +--> scored predictions written back to BigQuery
        |
        +--> FastAPI prediction endpoint on Cloud Run
        |
        v
Streamlit dashboard reading BigQuery marts and prediction outputs
```

Preferred GCP services:

- **Cloud Storage** for raw generated data.
- **BigQuery** for warehouse tables and marts.
- **Cloud Run** for a small FastAPI prediction service.
- **Artifact Registry** only if needed for container deployment.
- **Vertex AI** optional, not mandatory for v1.
- **Cloud Scheduler / Workflows** optional, only after the core project works.

Keep costs low. Use small synthetic datasets for cloud runs. Do not require paid always-on services.

## Scope Guardrails

Do not turn this into a huge MLOps platform. The purpose is employability signal, not enterprise completeness.

Must have:

- BigQuery warehouse path.
- A deployed or deployable Cloud Run API.
- Batch scoring that writes predictions to BigQuery.
- Tests and CI still pass locally.
- Clear README section showing cloud architecture and setup.
- Model card and business memo.

Nice to have:

- Simple drift or monitoring report.
- Vertex AI training job.
- Scheduled batch scoring.
- Looker Studio dashboard.

Avoid for v1:

- Kubernetes.
- Terraform unless the project is already stable.
- Overly complex feature store.
- Paid always-on infrastructure.
- Any real customer data.

## Implementation Phases

### Phase 1: Cloud Configuration Skeleton

Add configuration without breaking local mode.

Deliverables:

- `.env.example` entries for GCP project, region, bucket, BigQuery dataset.
- `src` or package config helper that supports `local` and `gcp` modes.
- README section: "Local mode vs GCP mode".
- No secrets committed.

Suggested env vars:

```text
NEOBANK_ENV=local|gcp
GCP_PROJECT_ID=
GCP_LOCATION=europe-west2
GCS_BUCKET=
BIGQUERY_DATASET=neobank_analytics
GOOGLE_APPLICATION_CREDENTIALS=
```

### Phase 2: Export Synthetic Data for Cloud

Add a command that creates cloud-ready data files.

Deliverables:

- Script/CLI command to export generated data to `data/cloud_export/`.
- Prefer Parquet if dependencies are already present; CSV is acceptable if simpler.
- Manifest JSON describing row counts, generation config, timestamp, and schema version.
- Test that export creates expected files and nonzero row counts.

Example command:

```text
uv run python -m neobank_product_analytics.cloud.export --profile portfolio
```

### Phase 3: Load to BigQuery

Add an upload/load path from local export to GCS and BigQuery.

Deliverables:

- Script/CLI to upload raw files to GCS.
- Script/CLI to create/load BigQuery raw tables.
- Idempotent behavior: reruns should replace a dev dataset or use a run ID.
- README setup instructions.

Example commands:

```text
uv run python -m neobank_product_analytics.cloud.upload_to_gcs --export-dir data/cloud_export
uv run python -m neobank_product_analytics.cloud.load_bigquery --run-id demo
```

### Phase 4: dbt on BigQuery

Port or parameterize dbt so it can run against BigQuery as well as DuckDB.

Deliverables:

- BigQuery dbt profile example.
- BigQuery-compatible models or adapter-safe SQL.
- `dbt build` succeeds on a small cloud dataset.
- Docs explain which models are shared vs BigQuery-specific.

Keep DuckDB support. The local project must remain reproducible without GCP.

### Phase 5: Propensity Model and Batch Scoring

Add one business-relevant model. Pick one:

- D7 activation propensity
- W4 retention propensity
- upsell / premium-feature propensity
- churn-risk proxy

Recommended first model:

**Upsell / high-value customer propensity**

Why: it maps well to Trustpilot pricing/monetization, ASOS customer marketing, Lendable customer management, and general commercial DS roles.

Deliverables:

- Feature builder reads BigQuery marts or local DuckDB marts.
- Train/evaluate script with train/test split, ROC-AUC, PR-AUC, calibration, segment checks.
- Batch scoring script writes predictions to BigQuery table, e.g. `ml_scores.customer_propensity`.
- Model artifact saved locally and optionally uploaded to GCS.
- Model card documenting objective, features, metrics, limitations, fairness/guardrail notes.

Example commands:

```text
uv run python -m src.modelling.train_propensity --backend bigquery
uv run python -m src.modelling.score_propensity --backend bigquery --write-table
```

### Phase 6: Cloud Run Prediction API

Deploy a small FastAPI service.

Minimum API:

- `GET /health`
- `POST /predict/activation` or `POST /predict/propensity`
- `GET /model/metadata`

Deliverables:

- `api/main.py`
- Dockerfile
- local API tests
- example request/response JSON
- deploy instructions for Cloud Run

Keep the API simple. It can use a packaged model artifact and lightweight request features. It does not need to query BigQuery on every request for v1.

### Phase 7: Dashboard Upgrade

Update the Streamlit dashboard to show cloud/product-readiness.

Deliverables:

- Dashboard can read from local DuckDB or BigQuery.
- Add model score distribution.
- Add top segments by predicted propensity.
- Add business action panel: recommended campaign/retention/upsell segments.
- Add data freshness and row-count checks.

### Phase 8: Monitoring-Style Report

Add a small monitoring/reporting artifact. This is not full production monitoring, but it should show awareness.

Deliverables:

- Script to compare latest scoring batch against training baseline.
- Report metrics:
  - row count
  - missingness by feature
  - prediction distribution
  - simple PSI or distribution shift for key features
  - model metric summary if labels are available
- Markdown or HTML report saved to `reports/model_monitoring/`.

### Phase 9: Documentation Polish

Final documentation should let a recruiter understand the project in 90 seconds.

Deliverables:

- README hero section renamed around business value:
  - "Customer Growth & Pricing ML Platform"
- Architecture diagram.
- "What this proves" section.
- "Run locally" section.
- "Run on GCP" section.
- "Cost controls" section.
- "Limitations" section.
- Links to:
  - model card
  - decision memo
  - dashboard screenshots
  - API docs
  - dbt docs if available

## Suggested Repository Structure

Adapt to the current repo rather than forcing this exact layout.

```text
neobank-product-analytics/
  api/
    main.py
    schemas.py
  cloud/
    README.md
    bigquery_schema/
    deploy_cloud_run.md
  docs/
    architecture/
    model_cards/
    memos/
  reports/
    model_monitoring/
  src/
    cloud/
      export.py
      upload_to_gcs.py
      load_bigquery.py
      bigquery_client.py
    modelling/
      train_propensity.py
      score_propensity.py
      monitor_propensity.py
  tests/
    test_cloud_export.py
    test_api.py
    test_propensity_scoring.py
```

## Recommended Libraries

Use existing dependencies where possible. Add only what is needed.

Likely additions:

- `google-cloud-storage`
- `google-cloud-bigquery`
- `dbt-bigquery`
- `fastapi`
- `uvicorn`
- `pydantic`
- `joblib`

Optional:

- `evidently` for monitoring, but a lightweight custom PSI report is probably enough.
- `great-expectations` is not necessary if dbt tests already cover data quality.

## Cost-Control Rules

- Use a small demo dataset for cloud examples.
- Put BigQuery dataset in a clear region, likely `EU` or `europe-west2`.
- Use `CREATE OR REPLACE` dev tables; avoid accidental table sprawl.
- Do not schedule recurring jobs until manual runs work.
- Document how to delete resources.
- Add a "cleanup" section with commands.

## README Positioning

The upgraded README should frame the project like this:

```text
This project simulates the analytics and ML workflow of a product/growth data scientist:
from raw customer event generation, through a tested metrics layer, causal experiment analysis,
propensity modelling, cloud batch scoring, and business-facing dashboards.
```

Use language that maps to target roles:

- customer growth
- pricing / monetization
- activation and retention
- acquisition and referral incrementality
- model deployment
- cloud warehouse
- reproducible analytics
- business decisioning

Avoid making it sound like only a toy fintech simulation. The synthetic data is acceptable if the engineering and methodology are strong.

## Job-Application Mapping

Use this mapping in the final docs or interview prep.

### ASOS Applied Scientist

Relevant proof:

- customer behaviour
- acquisition, engagement, retention
- incrementality
- experiments
- marketing/product optimisation

### Trustpilot GTM Applied AI / Pricing

Relevant proof:

- customer-level modelling
- monetization / upsell propensity
- pricing-adjacent decisioning
- BigQuery / GCP
- dashboards and stakeholder outputs

### Lendable Data Scientist

Relevant proof:

- fintech customer management
- pricing/commercial decisioning
- customer-level ML
- risk/propensity modelling
- Python + SQL

### Guardian Data Scientist

Relevant proof:

- conversion / churn / engagement
- segmentation
- BigQuery path
- business-facing recommendations

### Ipsos / WPP / marketing science roles

Relevant proof:

- experiment analysis
- incrementality
- customer segmentation
- automated analytical workflow

## Definition of Done

This upgrade is done when:

- Fresh clone can still run local demo.
- GCP path is documented and reproducible.
- BigQuery contains raw + transformed marts.
- A propensity model trains and scores.
- Scores are written back to BigQuery.
- Cloud Run API runs locally and has deployment instructions.
- Dashboard shows model/business outputs.
- Tests pass.
- README includes architecture, screenshots, setup, limitations.
- CV bullet can honestly say "GCP-deployed" or "GCP-ready" depending on whether deployment was actually completed.

Important wording:

- If actually deployed to GCP, say **GCP-deployed**.
- If only implemented with instructions and not deployed, say **GCP-ready** or **Cloud Run deployable**.
- Do not claim Vertex AI unless it is actually used.

## Suggested First Build Session

Start with the smallest vertical slice:

1. Add config/env handling.
2. Export synthetic data to cloud-ready files.
3. Upload/load one or two tables into BigQuery.
4. Run one simple BigQuery query from Python.
5. Document the setup.

That first slice is enough to unlock the rest without getting trapped in architecture.

