# Route C Public Claim Audit

> **Status:** clean (0 findings across 48 public surfaces) as of 2026-07-17,
> enforced continuously by `tools/release/claim_audit.py` +
> `tests/evidence/test_public_claims.py`. Release branch: **bigquery-only**
> (docs/adr/ADR-route-c-release-branch.md).

## What the audit enforces mechanically

1. **Forbidden wording** for this branch — "Looker experience", "validated
   LookML", "production scale", Monzo cost comparisons — may not appear
   affirmatively on any public surface (negated/governance mentions are
   recognised as such).
2. **Tracked numbers** (benchmark counts, percentages, spend figures) may only
   appear on public surfaces if the evidence registry anchors them.
3. An affirmative "validated" near "looker" without negation is flagged.

## Reconciliation of previously-known claim risks

| Claim risk | Resolution |
|---|---|
| Historical "13 raw tables / 107 checks" BigQuery record | Correctly labelled pre-pivot in README; superseded as *current* evidence by the dated 2026-07-17 run (68 models / 215 tests) — registry `current-counts-bigquery` vs `cloud-run-historical` |
| "Load manifest covers 16 raw tables" | Verified against `cloud/gcp/raw_bigquery_manifest.json` (claim inventory, Plan 1) |
| Streamlit `neobank-appuct-analytics` URL | Owner-confirmed deployment slug; registry `live-dashboard` (external) |
| Scheduled-jobs documentation contradiction (GCP_WAREHOUSE vs CLOUD_RUN_DEPLOYMENT) | Resolved with dated history in the Task 4 consolidation; both documents retain their dated records |
| Benchmark percentages (+1.95%, 62.7%, 523.9×) | Anchored in registry `benchmark-cost-result` with formulas, repetitions and pricing date; mixed result stated as measured |
| Looker status | `configured` only; the access limitation is stated wherever LookML is mentioned |

## Audit scope

`README.md`, `looker/README.md`, and every `docs/**/*.md`. Private
application material (Plan 4 Task 10) is generated from the registry and
checked at generation time.
