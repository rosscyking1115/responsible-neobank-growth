# Route C Consumer Map

> **Status:** Accepted 2026-07-17 (Plan 1, Task 5). Maps every current consumer surface
> to a proposed governed interface or an explicit decision. Companion to
> [route-c-model-inventory.csv](route-c-model-inventory.csv) and
> [route-c-migration-map.md](route-c-migration-map.md).

## Streamlit dashboard tabs (`app/streamlit_app.py`)

| Tab | Current data | Route C decision |
|---|---|---|
| Product health | `fct_activation`, `fct_weekly_engagement`, `fct_retention_cohorts`, `fct_feature_adoption` | Activation via `growth_acquisition` compatibility view; engagement/retention marts preserved unchanged |
| Customer outcomes | `fct_customer_outcomes`, wellbeing proxies, RBAC role selector | `growth_acquisition` guardrail fields via compatibility view; wellbeing/RBAC preserved |
| Digital inclusion | `fct_onboarding_funnel` | Funnel rebuilt on application events (`growth_acquisition`); tab keeps its contract via compatibility view |
| Customer protection | `fct_protection_events` | Preserved unchanged (outside the event boundary) |
| Pricing intelligence | pricing marts, fair-value governance | Preserved unchanged (bounded Finance = referral rewards only; pricing is a retained consumer domain) |
| Experiments | `fct_experiment_user_metrics`, `dim_experiment`, release engine | Downstream consumer of `growth_acquisition`; this is the G0.4 anchor consumer that must be servable entirely from governed interfaces |
| Monitoring | monitoring snapshot outputs | Feeds from `warehouse_health` once it exists; current snapshot preserved until then |

## FastAPI outputs (`api/main.py`)

| Route | Current data | Route C decision |
|---|---|---|
| `/health` | none | Preserve |
| `/score/activation` | activation model over `fct_activation` features | Downstream consumer; features served through `prs_ml_activation_features` (Plan 2) with compatibility contract |
| `/score/churn` | scoring artifacts | Preserve; same feature-interface route as activation |
| `/score/upsell` | scoring artifacts | Preserve; same feature-interface route as activation |
| `/recommend/offer` | pricing marts | Preserve (retained pricing domain) |
| `/simulate/pricing` | pricing scenario engine | Preserve (retained pricing domain) |

## Scheduled jobs and workflows

| Job | Decision |
|---|---|
| `.github/workflows/ci.yml` | Migrate: Plan 2 adds contract/fixture/oracle/standards jobs (Plan 2 Section 14) |
| `.github/workflows/monitoring-snapshot.yml` | Preserve; feeds `warehouse_health` local fields when the interface exists |
| `.github/workflows/keepalive.yml` | Preserve (pings the live dashboard URL) |
| Historical Cloud Scheduler jobs (`neobank-activation-score-load`, `neobank-score-monitoring`) | Historical evidence only (dated in `docs/CLOUD_RUN_DEPLOYMENT.md`); rerun decision belongs to Plan 3; the contradiction with `docs/GCP_WAREHOUSE.md` is resolved with dated history in Plan 4 |

## Real-data adapters

| Adapter | Decision |
|---|---|
| `src/adapters/uci_bank_marketing.py` | Preserve — method-validation consumer; reads its own real dataset, unaffected by the event boundary |
| `src/adapters/criteo_uplift.py` | Preserve — method-validation consumer; unaffected by the event boundary |

## Reports and artifacts

| Surface | Decision |
|---|---|
| Decision pack (`src/reports/decision_pack.py`) | Downstream consumer; reads compatibility relations during migration |
| Model card + monitoring reports | Preserve; regenerate only when their inputs change |

## Future Looker Explores (Plan 3)

| Explore | Source interface |
|---|---|
| `growth_acquisition` | `prs_growth_acquisition` |
| `referral_economics` | `prs_referral_economics` |
| `reward_reconciliation` | `prs_financial_reconciliation_daily` |
| `warehouse_health` | `prs_warehouse_health_daily` |

Looker connects only to governed presentation/logical relations — never to raw
payloads or version-specific landing models (ADR-route-c-dbt-looker-boundary).
