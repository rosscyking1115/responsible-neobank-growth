# Architecture

This project is a synthetic customer growth and pricing intelligence platform.
It keeps the local path fully reproducible while documenting the cloud path a
fintech team would use for a production version.

## Local Product Architecture

```mermaid
flowchart LR
    generator["Synthetic event generator"]
    raw["Local parquet raw zone"]
    duckdb["DuckDB warehouse"]
    dbt["dbt staging, intermediate, and mart models"]
    dashboard["Streamlit product dashboard"]
    api["FastAPI prediction and scenario contracts"]
    scoring["Batch activation scoring"]
    pricing["Pricing scenario runs"]
    monitoring["Monitoring and calibration reports"]

    generator --> raw
    raw --> duckdb
    duckdb --> dbt
    dbt --> dashboard
    dbt --> api
    dbt --> scoring
    dbt --> pricing
    scoring --> monitoring
    pricing --> monitoring
    api --> monitoring
```

## Cloud-Ready Target

```mermaid
flowchart LR
    source["Synthetic source events"]
    storage["Cloud Storage raw bucket"]
    bqraw["BigQuery raw datasets"]
    bqmarts["BigQuery dbt marts"]
    cloudrunapi["Cloud Run API service"]
    cloudrunjobs["Cloud Run batch jobs"]
    reports["Monitoring report artifacts"]
    streamlit["Streamlit dashboard"]

    source --> storage
    storage --> bqraw
    bqraw --> bqmarts
    bqmarts --> cloudrunapi
    bqmarts --> cloudrunjobs
    cloudrunjobs --> reports
    bqmarts --> streamlit
    reports --> streamlit
```

## Product Surfaces

- Streamlit dashboard: product health, pricing intelligence, experiments, and
  monitoring status.
- FastAPI service: activation, churn, upsell, offer recommendation, and pricing
  scenario contracts.
- Batch artifacts: activation score extracts, model monitoring reports, pricing
  scenario runs, and sensitivity CSVs.
- dbt warehouse: trusted marts for activation, retention, engagement, pricing,
  experiments, finance, and geo incrementality.

## Governance Boundaries

- All data is synthetic.
- The activation model is used for helpful onboarding prioritisation, not credit,
  eligibility, account limits, or punitive customer treatment.
- Pricing outputs are synthetic offer and incentive scenarios, not regulated
  credit pricing or real personalised pricing.
- Vulnerable-customer flags, complaint rates, support load, calibration, and
  drift are treated as release gates.
