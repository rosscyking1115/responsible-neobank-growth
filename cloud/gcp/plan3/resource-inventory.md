# Plan 3 Resource Inventory

> Prepared 2026-07-17 (Plan 3, Task 1). The **documented** state below comes
> from this repository's dated cloud evidence; the **live read-only inventory**
> (`bq ls`, `gcloud run services list`, `gcloud scheduler jobs list`) is
> executed at Task 2 start — it needs an authenticated session and is the first
> cloud action of the run (read-only, free).

## Documented existing resources (from repo evidence, not re-verified)

| Resource | Source of record | Status note |
|---|---|---|
| BigQuery datasets `neobank_raw`, marts (13-table/107-check run) | docs/GCP_WAREHOUSE.md | Historical (pre-pivot); not part of Plan 3 scope |
| Cloud Run service `neobank-api` + scoring/monitoring jobs | docs/CLOUD_RUN_DEPLOYMENT.md | Historical deployment evidence |
| Cloud Scheduler jobs (`neobank-activation-score-load`, `neobank-score-monitoring`) | docs/CLOUD_RUN_DEPLOYMENT.md | Documented as triggered; contradicts GCP_WAREHOUSE.md "not deployed" — known contradiction, resolved with dated history in Plan 4 |
| Budget + storage lifecycle policy | README (Cloud path) | Historical |

Plan 3 must not depend on, modify or delete any of the above; the live
inventory confirms whether they still exist and whether any scheduled job
could generate charges during the benchmark window (if so, it is flagged to
Ross before proceeding — not silently disabled).

## Live read-only inventory (executed 2026-07-17, authenticated as the owner)

- **Billing is NOT enabled** on `neobank-growth-platform-ross`: the project is
  in BigQuery **sandbox** mode. Nothing in the project can currently generate a
  charge; conversely, **DML is blocked** (empirically confirmed: a labelled
  MERGE probe failed with "DML queries are not allowed in the free tier"; the
  probe table was deleted). The incremental benchmark strategy requires DML, so
  the full F-versus-I comparison cannot run until billing is enabled — decision
  recorded with the user before proceeding.
- BigQuery datasets present (historical run): `neobank_raw`, `neobank_staging`,
  `neobank_intermediate`, `neobank_marts`, `neobank_ml`, `neobank_monitoring`.
- Cloud Run: service `neobank-api`; jobs `neobank-activation-score-load`,
  `neobank-score-monitoring` (dormant — no billing means no execution charges).
- Cloud Scheduler: not queryable while billing is disabled (API refuses);
  consistent with zero charge risk during the benchmark window.
- Plan 3 dataset created so far: `neobank_p3_raw_route_c_p3_20260717`
  (labelled, 30-day table expiry, europe-west2).

## Plan 3 resources to be created (after spend approval only)

| Resource | Name | Controls |
|---|---|---|
| Datasets ×5 | `neobank_p3_{raw,baseline,optimised,evidence,looker}_route_c_p3_20260717` | `route_c: plan3` labels, 30-day expiry, region `europe-west2` |
| Deployment identity | `route-c-p3-dbt@…` | create/update only Plan 3 datasets; run query jobs |
| Looker identity | `route-c-p3-looker@…` | read-only on governed interface + evidence datasets |

No credential file enters the repository; CI needs no cloud secrets.
