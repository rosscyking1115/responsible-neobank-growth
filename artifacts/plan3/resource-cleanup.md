# Plan 3 Resource Cleanup Record

> Recorded 2026-07-17 at the Plan 3 decision point.

## Already removed during the run

- `dml_probe` tables (both probes deleted immediately after use).
- Hung local runner processes (no cloud side effects).

## Intentionally retained (with reason and backstops)

| Resource | Reason | Backstops |
|---|---|---|
| 5 × `neobank_p3_*_route_c_p3_20260717` datasets + `neobank_p3b/p3o_20260717_*` model datasets | Retained until **2026-08-16** pending the possible Looker trial contact (validation would need the live interfaces); storage ~2 GB, inside the 10 GB free tier (£0) | 30-day default table expiry on the pre-created datasets; cleanup deadline in the runbook; deletion commands reviewed in `cloud/gcp/plan3/cleanup-runbook.md` |
| `neobank_p3_evidence_*.warehouse_job_evidence` + ablation table | Benchmark evidence mart (job metadata only, no query text) | Same expiry/deadline |
| Historical datasets (`neobank_raw`, `neobank_marts`, …) | Pre-existing project resources — out of Plan 3 scope, untouched | — |

## Not created (so nothing to clean)

- No service accounts were minted (owner-identity run; recorded deviation).
- No service-account keys exist anywhere.
- No Looker instance was provisioned; no schedules, no public links.
- No scheduled queries or transfers were created.

## Final deletion

Executed at or before **2026-08-16** per the runbook (or immediately after a
trial-validation upgrade completes, whichever is first), then recorded here by
dated addendum with the final `bq ls` audit.
