# Neobank Growth & Customer-Outcome Decision Platform

[![CI](https://github.com/rosscyking1115/neobank-product-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/rosscyking1115/neobank-product-analytics/actions/workflows/ci.yml)
[![Monitoring Snapshot](https://github.com/rosscyking1115/neobank-product-analytics/actions/workflows/monitoring-snapshot.yml/badge.svg)](https://github.com/rosscyking1115/neobank-product-analytics/actions/workflows/monitoring-snapshot.yml)

> A synthetic fintech decision-support platform that combines product analytics,
> experimentation, activation modelling, and pricing intelligence with
> customer-outcome guardrails — so a neobank can decide whether to **ship, iterate,
> or hold** a growth action while still protecting vulnerable customers.

[Live Streamlit Dashboard](https://neobank-appuct-analytics.streamlit.app/)

![Neobank product analytics dashboard](docs/assets/streamlit-product-health.png)

All data is synthetic. No real customer data, internal bank data, or proprietary
business metrics are used. See [Safety & Ethics](#safety--ethics).

---

## Why this project exists

In most analytics demos, growth is the only goal: increase activation, conversion,
retention, or margin. In financial services that framing is dangerous. A bad
e-commerce discount wastes money; a bad fintech growth decision can push a
vulnerable customer toward a worse financial outcome.

This project asks a sharper question than "does this action grow a metric?":

> Can we grow activation, retention, referrals, and pricing conversion **while still
> delivering good customer outcomes** — and is the evidence strong enough to act?

Every analysis therefore ends in a **decision with guardrails** (e.g. `ship` /
`iterate` / `hold`, or `target` / `monitor` / `do_not_target`), not just a chart.

## What decisions it supports

| Question a growth/product team asks | What the platform provides |
| --- | --- |
| Should we ship this onboarding treatment? | D7 activation A/B readout with CUPED, SRM, and customer-outcome guardrails. |
| Which users need onboarding **help** (not upsell)? | Calibrated activation model that targets *low-propensity* users, with a vulnerable-customer review path. |
| Are referral incentives genuinely incremental? | Geo difference-in-differences with parallel-trends, placebo, and synthetic-control checks. |
| Which pricing/incentive offers are attractive *after* guardrails? | Offer economics + recommendation mart + scenario runs with margin, complaint, support, and vulnerable-share guardrails. |
| Is the data/model still safe to operate? | Monitoring snapshot, calibration report, drift checks, and release gates. |

## How it works (end to end)

```text
Synthetic event generator  (users, transactions, sessions, features, support,
        |                    referrals, pricing offers, experiment assignments)
        v
DuckDB / Parquet  ──►  dbt metrics layer  ──►  Streamlit dashboard
        |                (staging + product / pricing / experiment / geo marts)
        |
        ├──►  Modelling + experiments  ──►  model card, decision memos, monitoring
        |
        └──►  FastAPI service  ──►  scoring, offer, and pricing-scenario contracts
                                     (each response carries guardrail flags)

Optional GCP path:
   Cloud Storage  ──►  BigQuery (raw + marts)  ──►  Cloud Run jobs + private API
                                                     ──►  Cloud Scheduler + Monitoring
```

## What's built today

- **Synthetic data generation** — deterministic, seeded `polars` generator covering
  users, transactions, sessions, feature adoption, support contacts, referrals,
  pricing offers, and experiment assignments with embedded ground truth.
- **dbt metrics layer** — staging models plus product, pricing, experiment, geo, and
  finance marts (DuckDB locally; BigQuery as an optional target).
- **Activation decisioning model** — logistic pipeline with **isotonic calibration on
  a forward time window**, threshold economics, segment checks, a published
  [model card](docs/model_cards/MODEL_ACTIVATION_DECISIONING.md), an artifact registry,
  and batch scoring.
- **Experimentation & causal inference** — Welch difference-in-means, **CUPED**
  variance reduction, **SRM** checks, heterogeneous effects, confidence-interval-based
  guardrails, **difference-in-differences with clustered standard errors**, parallel
  trends, placebo-in-space, and synthetic control.
- **Pricing intelligence** — observed offer economics, a recommendation mart, and
  scenario + sensitivity runs that score margin against fair-value, vulnerable-share,
  complaint, and human-review guardrails.
- **FastAPI service** — `/health`, `/score/{activation,churn,upsell}`,
  `/recommend/offer`, and `/simulate/pricing`. Every response returns a decision,
  reason codes, and explicit guardrail flags.
- **Streamlit dashboard** — product health, **customer outcomes & fairness**, **digital
  inclusion**, **customer protection**, pricing intelligence, experiments, and
  monitoring views over the dbt marts. The customer outcomes tab shows segment fairness
  gaps and a live release-gate verdict; digital inclusion shows the onboarding funnel
  and abandonment by segment; customer protection shows scam-intervention outcomes.
- **Monitoring & operations** — a monitoring snapshot, model and calibration reports,
  release checks, and an operations runbook.
- **Cloud path (GCP)** — repeatable plan generators and Cloud Run job entrypoints for
  GCS landing, BigQuery load/verify/monitoring, private API and job deployment,
  scheduling, and cost controls.
- **Financial wellbeing layer** — synthetic, clearly-bounded per-customer wellbeing
  and vulnerability proxies with **executable use-boundary guardrails** (permitted vs
  prohibited uses) and segment outcome / fairness-gap metrics. See
  [docs/FINANCIAL_WELLBEING_PROXIES.md](docs/FINANCIAL_WELLBEING_PROXIES.md).
- **Responsible release-gate engine** — turns evidence + customer-outcome guardrails
  into an explainable `ship / limited_rollout / experiment_only / needs_human_review /
  block` decision, where harm signals always dominate commercial uplift. See
  [docs/RELEASE_DECISION_FRAMEWORK.md](docs/RELEASE_DECISION_FRAMEWORK.md).
- **Fair-value pricing governance** — scores each offer's fair value from observed
  customer-outcome guardrails and downgrades commercially attractive but unfair offers
  to hold or human review. See [docs/FAIR_VALUE_PRICING.md](docs/FAIR_VALUE_PRICING.md).
- **Digital inclusion & onboarding funnel** — synthetic KYC funnel plus analysis of
  who drops out, which segments are underserved, and who needs an assisted journey.
  See [docs/DIGITAL_INCLUSION.md](docs/DIGITAL_INCLUSION.md).
- **Customer-protection / scam-intervention simulation** — risk-triggered *supportive*
  responses (education, soft friction, cooling-off, human review) on transfers;
  explicitly not a fraud engine. See
  [docs/CUSTOMER_PROTECTION_SIMULATION.md](docs/CUSTOMER_PROTECTION_SIMULATION.md).
- **Quality** — 175 `pytest` tests, `ruff` lint, a GitHub Actions CI pipeline (lint →
  tests → dbt build → container build → API smoke test), and a scheduled monitoring
  workflow.

## Customer-outcome guardrails

Guardrails are first-class outputs, not an afterthought. They are already wired into
the code:

- **Scoring** — an age block, a vulnerable-customer review flag, and an activation
  model that targets users who need *help* rather than upselling them.
- **Experiments** — guardrails are evaluated on the **confidence interval**, not just
  the point estimate, across complaint, support-contact, and app-stability metrics.
- **Pricing** — recommendations are gated on positive incremental unit economics,
  vulnerable-customer share, 14-day complaint rate, and human-review load.
- **Monitoring** — the snapshot fails the build on missing marts or an elevated
  complaint rate and warns on weak activation, margin, or review load.

## Technology stack

| Layer | Tools |
| --- | --- |
| Data generation | Python, `polars`, Faker-style synthetic events, Parquet |
| Analytics engineering | dbt, DuckDB, BigQuery |
| Experimentation | CUPED, SRM, CI-based guardrails, DiD, synthetic control |
| Modelling | scikit-learn, isotonic calibration, model card, batch scoring |
| Application | Streamlit dashboard, FastAPI prediction service |
| Cloud | Cloud Storage, BigQuery, Cloud Run, Cloud Scheduler, Cloud Monitoring |
| Quality | pytest, ruff, GitHub Actions, monitoring snapshot workflow |

## Quickstart (no cloud required)

The full local path builds a synthetic dataset, dbt marts, tests, and the dashboard.

```powershell
uv sync --group dev
uv run python -m data_generator.generate --users 5000 --months 6 --output-dir raw/ci
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank
uv run pytest
uv run streamlit run app/streamlit_app.py
```

For a portfolio-size dataset:

```powershell
uv run python -m data_generator.generate --users 50000 --months 12 --output-dir raw/portfolio_full
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank --vars "{raw_path: raw/portfolio_full}"
```

Run the API locally:

```powershell
uv run uvicorn api.main:app --reload   # then open http://127.0.0.1:8000/docs
```

## Five-minute review guide

1. Open the [live dashboard](https://neobank-appuct-analytics.streamlit.app/).
2. Read the [case study](docs/CASE_STUDY.md) — decisions supported, evidence, limits.
3. Skim the [architecture](docs/ARCHITECTURE.md) and [API contract](docs/API.md).
4. Review the [model card](docs/model_cards/MODEL_ACTIVATION_DECISIONING.md) and
   [operations runbook](docs/OPERATIONS_RUNBOOK.md).

## Documentation

| Document | Purpose |
| --- | --- |
| [docs/CASE_STUDY.md](docs/CASE_STUDY.md) | Business-facing case study, decisions, evidence, and limitations. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Local and cloud architecture overview. |
| [docs/API.md](docs/API.md) | Prediction and pricing-scenario API contract. |
| [docs/PRICING_SCENARIOS.md](docs/PRICING_SCENARIOS.md) | Pricing recommendation and scenario framework. |
| [docs/MONITORING.md](docs/MONITORING.md) | Data, model, score, and GCP monitoring checks. |
| [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md) | Rollback triggers, triage, and GCP operations. |
| [docs/CLOUD_RUN_DEPLOYMENT.md](docs/CLOUD_RUN_DEPLOYMENT.md) | Private Cloud Run API and job deployment. |
| [docs/GCP_WAREHOUSE.md](docs/GCP_WAREHOUSE.md) | Cloud Storage and BigQuery warehouse path. |

## Cloud path

The GCP path has been exercised beyond local development: a Cloud Storage landing
zone loaded into BigQuery, a dbt graph run against BigQuery, an activation score
extract and monitoring result written to BigQuery, a private Cloud Run API and
Cloud Run scoring/monitoring jobs, Cloud Scheduler runs, and Cloud Monitoring alert
policies plus a budget and storage-lifecycle policy for cost control. See
[docs/CLOUD_RUN_DEPLOYMENT.md](docs/CLOUD_RUN_DEPLOYMENT.md) and
[docs/GCP_WAREHOUSE.md](docs/GCP_WAREHOUSE.md) for the recorded evidence.

> The recorded BigQuery figures (13 raw tables, 107 dbt checks) reflect the cloud run
> *before* the responsible-growth pivot. The load manifest now covers all 16 raw
> tables; the new wellbeing, inclusion, and protection tables and marts are exercised
> locally and would be reloaded on the next GCP run.

## Responsible Growth pivot

The platform has been deepened into a **Responsible Neobank Growth & Financial
Wellbeing Decision Platform** — connecting commercial growth with customer-outcome,
fairness, inclusion, and protection guardrails. All six pivot modules are built:

1. ✅ **Financial wellbeing layer** — [docs/FINANCIAL_WELLBEING_PROXIES.md](docs/FINANCIAL_WELLBEING_PROXIES.md)
2. ✅ **Responsible release-gate engine** — [docs/RELEASE_DECISION_FRAMEWORK.md](docs/RELEASE_DECISION_FRAMEWORK.md)
3. ✅ **Customer Outcomes & Fairness page** — segment fairness gaps + live release-gate verdict
4. ✅ **Fair-value pricing governance** — [docs/FAIR_VALUE_PRICING.md](docs/FAIR_VALUE_PRICING.md)
5. ✅ **Digital inclusion & onboarding funnel** — [docs/DIGITAL_INCLUSION.md](docs/DIGITAL_INCLUSION.md)
6. ✅ **Customer-protection / scam-intervention simulation** — [docs/CUSTOMER_PROTECTION_SIMULATION.md](docs/CUSTOMER_PROTECTION_SIMULATION.md)

## Safety & ethics

This project uses **synthetic data** and is **not** a production banking, fraud,
credit, eligibility, or financial-advice system. Vulnerability and wellbeing fields
are synthetic proxies for evaluating product decisions and must not be used to deny
services, set prices unfairly, determine creditworthiness, or make punitive
decisions. It does not represent any real financial institution.

## What would be hardened for production

A regulated deployment would add stronger API protection (API Gateway / IAP / JWT,
rate limits, structured logging); formal data governance (row/column controls,
retention, lineage, cost controls); keyless OIDC CI/CD with image scanning, SBOMs,
and IaC; a model registry / feature store with shadow deployments and
online/offline parity; and formal privacy, Consumer Duty, model-risk, and approval
controls before any live customer decisioning.

## License

See [LICENSE](LICENSE).
