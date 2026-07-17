# ADR: Route C Plan 2 decision

## Status

Accepted — 2026-07-17 (Plan 2, Task 12). Outcome recorded: **go-to-plan-3**.
**User (Ross) reviewed and accepted the Plan 2 result on 2026-07-17.** Plan 3
may begin its £0 preflight work; **no billable cloud action is authorised until
the user separately approves the Plan 3 spend preflight** (Plan 3 §5.1).

## Context

Gate 0 (`go`, user-accepted 2026-07-17) authorised Plan 2 to implement the
event-to-interface warehouse locally: the deterministic generator, four-layer
models, incremental correctness, reward reconciliation, compatibility paths,
real-manifest standards enforcement and BigQuery-compilation readiness. Three
outcomes were allowed: `go-to-plan-3`, `revise`, `route-b-fallback`.

## Decision

**go-to-plan-3.** All nine acceptance gates (P2.1–P2.9) pass with evidence in
[artifacts/plan2/verification-results.json](../../artifacts/plan2/verification-results.json),
summarised in
[artifacts/plan2/verification-summary.md](../../artifacts/plan2/verification-summary.md).

Deciding factors:

- the blue/green oracle reached **exact parity** between full-refresh and
  chronological incremental builds at every governed interface, with the
  beyond-lookback failure demonstrated in isolation and recovered by a bounded,
  recorded backfill — the correctness question Plan 2 existed to answer;
- the built warehouse reproduces the generation manifest's truth exactly
  (ledger totals, exception identities, lifecycle states);
- the anchor consumer runs unchanged on governed-interface data, and no
  existing model or evidence was deleted — no fallback trigger (Plan 2 §17)
  fired;
- £0 cloud spend; BigQuery remains configured-not-executed; no Looker claim.

## Consequences

- Plan 3 (BigQuery benchmark + Looker trial) is authorised **on user
  acceptance plus a separate spend-preflight approval**; its preconditions
  (Plan 3 §3) additionally require generating the `standard` profile with a
  run manifest — recorded as an open item here, expected at Plan 3 preflight
  alongside generator performance work (validator caching).
- Open items in the verification summary (manifest/meta mechanical
  cross-check, compatibility name-swap gate, clean-clone reproduction) carry
  forward visibly and must not silently disappear.
- If Plan 3 stops for spend, access or correctness, the project retains all
  Plan 2 local evidence without inflated cloud claims (Plan 3 §1).
