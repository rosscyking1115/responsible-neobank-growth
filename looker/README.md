# Looker Semantic Layer — Architecture and LookML (Plan 3, Task 9)

> **Status:** LookML **authored locally** on 2026-07-17 against the
> parity-proven BigQuery interfaces (optimised lineage,
> `neobank_p3o_20260717_*`). **No Looker instance has validated this yet** —
> validation happens in the 14-day trial (LookML/SQL/Assert/Content
> validators) and no Looker experience is claimed until it does
> (claim level: `configured`).
>
> Implementation deviation from the Plan 1 field inventory: the
> `reward_reconciliation` Explore keys on `referral_id` + `reconciliation_date`
> (not `reward_id` + date) because a missing posting has no reward identifier —
> the exception the interface exists to expose.

## Responsibility boundary

Locked by [ADR-route-c-dbt-looker-boundary](../docs/adr/ADR-route-c-dbt-looker-boundary.md):
dbt owns dedup/state/eligibility/reconciliation and persisted grains; LookML owns
naming, additive measures, Explore joins, drills and dashboards. LookML never
reimplements business logic. Looker connects only to governed
presentation/logical relations.

## Planned project layout (Plan 3)

```text
looker/
  responsible_neobank.model.lkml
  manifest.lkml
  views/
    growth_acquisition.view.lkml
    referral_economics.view.lkml
    reward_reconciliation.view.lkml
    warehouse_health.view.lkml
  dashboards/
    responsible_growth.dashboard.lookml
    reward_reconciliation.dashboard.lookml
    warehouse_health.dashboard.lookml
  tests/
    model_tests.lkml
```

Field/measure inventory: [docs/looker/explore-field-inventory.csv](../docs/looker/explore-field-inventory.csv).
Trial execution order: [docs/looker/trial-runbook.md](../docs/looker/trial-runbook.md).
Evidence capture: [docs/looker/evidence-checklist.md](../docs/looker/evidence-checklist.md).

## Explores

### growth_acquisition

- **growth_acquisition question:** where do applicants progress or drop between
  application, approval and funded activation, by campaign/referral cohort and
  synthetic outcome guardrail?
- **growth_acquisition primary key:** `application_id` on `prs_growth_acquisition`.
- **growth_acquisition join:** one-to-one to experiment arm attributes on
  `application_id`; measures are fanout-safe because the grain is one row per
  application journey.

### referral_economics

- **referral_economics question:** how many incremental activated customers and
  what booked reward cost are associated with each referral cohort or experiment?
- **referral_economics primary key:** `referral_id` on `prs_referral_economics`.
- **referral_economics join:** many-to-one from referral to campaign cohort;
  drill path to reward/reconciliation status by `reward_id`.

### reward_reconciliation

- **reward_reconciliation question:** which expected referral rewards are
  missing, duplicated, mismatched, stale or incorrectly reversed?
- **reward_reconciliation primary key:** composite `reward_id` +
  `reconciliation_date` on `prs_financial_reconciliation_daily`.
- **reward_reconciliation join:** one-to-many drill from daily aggregate variance
  to fictional event trace; additive money measures stay at the declared grain.

### warehouse_health

- **warehouse_health question:** which models/interfaces are stale, failing,
  expensive or slower than their measured baseline?
- **warehouse_health primary key:** composite `model_name` + `run_date` on
  `prs_warehouse_health_daily`.
- **warehouse_health join:** none required for the core Explore; cost fields stay
  null until Plan 3 measurement exists.

## Quality rules the LookML must satisfy (Plan 3 gate)

Every view declares a correct primary key; every join declares a relationship
matching the dbt grain; fanout tests cover one-to-many paths; ratios use governed
numerators/denominators (no average-of-averages); minor-unit currency is
converted for display only; synthetic/illustrative fields carry descriptions;
datagroups use real warehouse freshness; every dashboard tile traces to a
governed Explore.
