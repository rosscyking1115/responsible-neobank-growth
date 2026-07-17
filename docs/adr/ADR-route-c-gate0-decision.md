# ADR: Route C Gate 0 decision

## Status

Accepted — 2026-07-17 (Plan 1, Task 10). Outcome recorded: **go**.
Plan 2 execution begins only after the user reviews and **accepts** this result
(Plan 1 §17); this ADR does not by itself start Plan 2.

## Context

Plan 1 froze the Route C contracts and asked one falsifiable question: can the
project migrate to a versioned event boundary and governed four-layer warehouse
without destroying valid Growth evidence, duplicating business logic or
expanding into a general banking simulator? Four outcomes were allowed:
`go`, `revise`, `fallback-to-route-b`, `stop`.

## Decision

**go.** All eight mandatory Gate 0 gates pass with evidence paths recorded in
[artifacts/gate0/route-c-gate0-results.json](../../artifacts/gate0/route-c-gate0-results.json)
and summarised in
[artifacts/gate0/route-c-gate0-report.md](../../artifacts/gate0/route-c-gate0-report.md).

Deciding factors:

- the baseline reproduced exactly (217 tests, 133 dbt checks, 16 raw tables),
  so preservation is measured against verified reality, not README claims;
- the migration inventory classified all 50 assets with zero unclassified rows,
  and every validated capability has a compatibility route — no fallback trigger
  (Plan 1 §15) fired;
- the hand-built truth fixtures proved the contracts express duplicates, late
  arrivals, reversals, malformed payloads, schema evolution and reconciliation
  breaks with exact, independently recomputed truth;
- scope held: 12 event schemas across the six locked families, Finance bounded
  to the referral-reward subledger, no forbidden expansion;
- £0 cloud spend; Looker prepared but neither activated nor claimed.

## Consequences

- Plan 2 (event-to-interface warehouse) is authorised on user acceptance, with
  the bounded scope listed in the Gate 0 report; Plans 3–4 remain blocked on
  their own gates.
- The limitations carried forward (documentation contradiction for Plan 4;
  remaining exception fixtures, beyond-lookback fixture and grain confirmations
  for Plan 2) are recorded in the report and must not silently disappear.
- If Plan 2 hits a stop condition (Plan 2 §17), the decision framework returns
  here: Route B fallback remains available and is not project failure.
