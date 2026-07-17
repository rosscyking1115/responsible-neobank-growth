# BigQuery Budget and Cleanup Runbook

> **Status:** controls specified 2026-07-17 (Plan 1, Task 10). **Nothing here has
> been executed** — Plan 1 authorises £0 of new billable cloud work. These are
> the controls Plan 3 must apply before its first billable query, with
> placeholders for the values fixed at Plan 3 preflight.

## Honest framing

**Billing budgets and alerts are not hard caps.** An alert fires after spend has
happened. Safety in this project relies on query quotas, `maximum_bytes_billed`,
bounded inputs, staged execution and manual stop conditions — never on alerts
alone. No document in this repository may describe an alert as something that
stops a charge before it occurs.

## Separate execution approval

Accepting a plan approves a design, not an unknown bill. Before the first
billable query, Plan 3 produces a preflight record (`cloud/gcp/plan3/spend-preflight.md`)
containing current official pricing references, dry-run byte estimates per
phase, repetition counts, billing state, the proposed ceiling and exact deletion
deadlines. Any expected charge requires **explicit user acceptance** of that
record. Default proposed ceiling: £10 incremental; lower preferred; no overage.

## Query controls (fixed now, applied in Plan 3)

- `maximum_bytes_billed` stays enabled and defaults to **1 GB** per query
  (already present in `dbt_neobank/profiles.yml` via
  `NEOBANK_BQ_MAX_BYTES_BILLED`); exceptions require a recorded dry run, reason
  and per-query ceiling;
- project-level custom query **quota** configured to the lowest practical value
  before execution;
- required partition filters on large event tables where supported;
- a pre-run **dry run** records estimated bytes for every known stage;
- a post-run query records bytes processed/billed, slot milliseconds and runtime
  from `INFORMATION_SCHEMA.JOBS`;
- every dbt invocation and benchmark phase carries labels/query comments for
  attribution (`route_c_plan3`, run id, strategy, phase);
- hard stop when cumulative observed/estimated spend reaches **80% of the
  approved ceiling**;
- scheduled queries stay disabled unless part of a single bounded test.

## Resource isolation (placeholders fixed at preflight)

| Item | Placeholder |
|---|---|
| Datasets | `neobank_p3_{raw,baseline,optimised,evidence,looker}_<run_id>` |
| Labels | `route_c_plan3`, dated run identifier |
| Dataset **expiry** / deletion deadline | set at preflight; recorded in the run config |
| Identities | deployment/dbt identity (Plan 3 datasets only); Looker read-only identity |
| Region | fixed once at preflight; no cross-region copies |

## Cleanup checklist (verified before provisioning, executed before close)

- [ ] revoke/delete temporary service-account keys or credentials
- [ ] disable Looker schedules and public links; confirm trial expiry/non-conversion
- [ ] export permitted LookML and evidence
- [ ] delete scratch/baseline/optimised datasets after evidence capture
- [ ] retain only the approved minimal evidence dataset if free and useful
- [ ] inspect final billing/job inventory (`INFORMATION_SCHEMA.JOBS` extract)
- [ ] record intentionally retained resources and why
- [ ] confirm cleanup commands target only labelled Plan 3 resources

## Stop conditions

Stop all new cloud execution and begin cleanup when spend reaches 80% of the
ceiling; when correctness fails beyond one bounded iteration; when job
attribution cannot isolate benchmark work; when any trial requests unapproved
payment; or when a credential or unrelated dataset enters scope.
