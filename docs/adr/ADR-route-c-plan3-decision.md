# ADR: Route C Plan 3 decision

## Status

Accepted — 2026-07-17 (Plan 3, Task 12). Outcome recorded:
**partial go — BigQuery only**.
Plan 4 execution begins only after the user reviews and **accepts** this
result; publication and release decisions remain Plan 4's own gates.

## Context

Plan 3 had two questions: how full-refresh and incremental processing compare
on BigQuery for the same final event state, and whether governed LookML
Explores can be genuinely validated in a no-cost trial. Four outcomes were
allowed: `go to Plan 4`, `partial go — BigQuery only`, `revise`,
`stop cloud work`.

## Decision

**partial go — BigQuery only.**

**BigQuery: complete and valid.** All applicable gates (P3.1–P3.5, P3.8) pass:

- spend controlled end to end: preflight approved before any billable action,
  844 attributed jobs, 32.99 GB billed ≈ **£0.21 estimated (likely £0 under
  the free tier)** against the £10 ceiling; every resource labelled, probes
  deleted, retention recorded with backstops
  ([resource-cleanup](../../artifacts/plan3/resource-cleanup.md));
- the current graph (68 models, 215 tests) has a dated BigQuery run
  superseding the historical 13-table/107-check record;
- source and interface correctness are exact at every phase
  (base/delta/repair parity artifacts);
- the **measured result is mixed and reported as such**: incremental billed
  **+1.95% more bytes** than full rebuild on the unpartitioned raw store while
  using **62.7% less compute** (median slot-ms), and the ablation shows the
  same query processing **523.9× fewer bytes on partitioned storage** —
  absolute values, formulas, repetitions and the pricing date are in
  [benchmark-summary.json](../../artifacts/plan3/benchmark-summary.json) and
  [warehouse-cost-results.csv](../../artifacts/plan3/warehouse-cost-results.csv);
  no extrapolation to production or Monzo scale;
- the at-scale repair proof surfaced and fixed two real staleness defects
  (unresolved references; stale ledger lines) with self-healing re-selection
  and new invariants — failure-and-recovery evidence retained.

**Looker: access-limited, honestly recorded.** The trial signup returned a
sales-contact outcome with no instance provisioned (run record, 2026-07-17).
Per §14.4: the authored LookML is retained at claim level **configured**; no
BI substitute was used; **no Looker execution or experience is claimed**.
Gates P3.6–P3.7 are recorded as *not achieved — access limited*, which is
exactly what this outcome branch exists for.

## Consequences

- Plan 4 proceeds on the **BigQuery-only release branch** (Plan 4 §2.2): no
  "Looker experience" or "validated LookML" wording anywhere; the gap is
  stated plainly in the case study and application material.
- **Upgrade path:** if a genuine no-cost trial is provisioned before the
  cleanup deadline (2026-08-16), the validation stage (Plan 3 Tasks 10–11)
  runs and this ADR is upgraded by dated addendum. Payment or auto-conversion
  requests end the trial path immediately.
- Cloud resources are retained until the deadline with recorded reasons and
  auto-expiry backstops, then deleted per the runbook.
