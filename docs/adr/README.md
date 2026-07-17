# Architecture Decision Records

Route C reframed this repository into an event-to-interface Analytics
Engineering platform. These ADRs separate accepted current decisions from
superseded, historical and rejected ones so reviewers do not read stale
documents as current architecture.

## Accepted — current architecture

| ADR | Decision |
|---|---|
| [Event boundary](ADR-route-c-event-boundary.md) | Versioned synthetic backend events with a shared envelope replace the batch source boundary |
| [Four-layer interfaces](ADR-route-c-four-layer-interfaces.md) | `landing → normalised → logical → presentation`; only normalised/logical become governed interfaces; compatibility, never one-commit renames |
| [dbt/LookML boundary](ADR-route-c-dbt-looker-boundary.md) | dbt owns business logic and one authoritative grain per metric; LookML owns naming, joins, dashboards only |
| [Synthetic truth](ADR-route-c-synthetic-truth.md) | Three claim levels — engineering truth, analytical method validation, illustrative magnitude |
| [Release branch](ADR-route-c-release-branch.md) | BigQuery-only release: BigQuery executed and measured; LookML authored/configured, not validated |

## Gate and phase decisions (dated)

| ADR | Outcome |
|---|---|
| [Gate 0](ADR-route-c-gate0-decision.md) | **go** — contracts express the hard cases; migration preserves validated capability (2026-07-17) |
| [Plan 2](ADR-route-c-plan2-decision.md) | **go-to-plan-3** — local event warehouse with exact full/incremental parity (2026-07-17) |
| [Plan 3](ADR-route-c-plan3-decision.md) | **partial go — BigQuery only** — benchmark measured (mixed result); Looker access-limited (2026-07-17) |

## Rejected routes (recorded in the ADRs above)

- **Route B** (keep batch sources) — retained as the explicit fallback; not
  triggered.
- **Kafka / streaming** — out of scope; the project proves warehouse-side
  correctness, not transport.
- **dbt Semantic Layer** — not adopted; the project uses governed dbt
  marts/interfaces and does not claim Semantic Layer usage.
- **One-commit model renames** — forbidden by the compatibility rule.

## Historical evidence

Earlier deployment and warehouse runs (Cloud Run API/jobs, the 2026-05-30/31
13-table/107-check BigQuery demo) are dated historical records in
[CLOUD_RUN_DEPLOYMENT.md](../CLOUD_RUN_DEPLOYMENT.md) and
[GCP_WAREHOUSE.md](../GCP_WAREHOUSE.md); the scheduled-jobs status is reconciled
there with dated history. Current cloud evidence is the 2026-07-17 BigQuery
benchmark ([run record](../../artifacts/plan3/run-record.md)).
