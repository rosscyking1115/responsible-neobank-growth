# BigQuery Budget and Cleanup Runbook

> **Status:** the cost controls applied to the BigQuery benchmark. These are the
> controls fixed before the first billable query, with placeholders for the values
> resolved at preflight.

## Honest framing

**Billing budgets and alerts are not hard caps.** An alert fires after spend has
happened. Safety in this project relies on query quotas, `maximum_bytes_billed`,
bounded inputs, staged execution and manual stop conditions — never on alerts
alone. No document in this repository may describe an alert as something that
stops a charge before it occurs.

## Separate execution approval

Accepting a plan approves a design, not an unknown bill. Before the first
billable query, the benchmark produces a preflight record containing current
official pricing references, dry-run byte estimates per
phase, repetition counts, billing state, the proposed ceiling and exact deletion
deadlines. Any expected charge requires **explicit user acceptance** of that
record. Default proposed ceiling: £10 incremental; lower preferred; no overage.

## Query controls (fixed now, applied in the BigQuery benchmark)

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
  attribution (project, run id, strategy, phase);
- hard stop when cumulative observed/estimated spend reaches **80% of the
  approved ceiling**;
- scheduled queries stay disabled unless part of a single bounded test.

## Resource isolation (placeholders fixed at preflight)

| Item | Placeholder |
|---|---|
| Datasets | `neobank_p3_{raw,baseline,optimised,evidence}_<run_id>` |
| Labels | project label, dated run identifier |
| Dataset **expiry** / deletion deadline | set at preflight; recorded in the run config |
| Identities | deployment/dbt identity |
| Region | fixed once at preflight; no cross-region copies |

## Cleanup checklist (verified before provisioning, executed before close)

- [ ] revoke/delete temporary service-account keys or credentials
- [ ] delete scratch/baseline/optimised datasets after evidence capture
- [ ] retain only the approved minimal evidence dataset if free and useful
- [ ] inspect final billing/job inventory (`INFORMATION_SCHEMA.JOBS` extract)
- [ ] record intentionally retained resources and why
- [ ] confirm cleanup commands target only labelled benchmark resources

## Stop conditions

Stop all new cloud execution and begin cleanup when spend reaches 80% of the
ceiling; when correctness fails beyond one bounded iteration; when job
attribution cannot isolate benchmark work; when any trial requests unapproved
payment; or when a credential or unrelated dataset enters scope.
