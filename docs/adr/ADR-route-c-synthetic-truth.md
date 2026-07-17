# ADR: Route C synthetic truth contract

## Status

Accepted — 2026-07-17 (Plan 1, Task 2).

## Context

The project already separates ground-truth-validated methods from illustrative
magnitudes (`docs/CREDIBILITY.md`). Route C turns synthetic data into a deterministic,
failure-injected *event benchmark*, which needs a stricter contract: every scenario's
outcome must be known exactly before the warehouse processes it, or the correctness
oracles prove nothing.

## Decision

Every public or internal result derived from the synthetic events uses exactly one of
three claim levels:

1. **engineering truth** — exact outcomes known from the generator's truth manifest
   (event counts, duplicates, quarantined records, lifecycle end states, ledger and
   exception totals);
2. **analytical method validation** — causal/statistical recovery against seeded
   truth and the existing real-data adapters (UCI Bank Marketing, Criteo Uplift);
3. **illustrative business magnitude** — explicitly not evidence about real
   customers or Monzo.

Generator profiles are locked: `tiny` (≤5,000 events; every mandatory failure
scenario; exact truth committed), `standard` (later public benchmark; design only in
Plan 1), `stress` (deferred). Each scenario declares a truth manifest: seed and
generator version, event counts, expected duplicates and quarantines, late-arrival
windows, lifecycle end states, reward entitlements/postings/settlements/reversals,
reconciliation exceptions with reason codes, seeded experiment effects, and
prohibited interpretations.

Gate 0 requires one hand-built tiny referral fixture containing: a valid settled
qualification; a duplicated delivery sharing an idempotency key; a qualification
arriving after the processing watermark; a booked reward later reversed; a malformed
v2 payload sent to quarantine; an intentionally missing reward posting — with exact
expected daily entitlement, ledger and exception totals.

## Alternatives considered

- **Statistical realism as the goal:** rejected — imitation of real customers is
  explicitly out of scope; the value is exact, auditable truth, not plausibility.
- **Generator-first (build the big generator, then derive truth):** rejected — the
  hand-built truth case proves the contracts can express the difficult cases before
  thousands of rows exist.

## Consequences

- The tiny fixtures become the reliability oracle for Plans 2–3: dropped late
  events, duplicate counting, incorrect reversal treatment and missing postings must
  be *detectable*, not just documented.
- Credibility language gains a third, sharper category (engineering truth) on top of
  the existing 🟢/🟡 split; no category may be silently promoted.
- Publishing any synthetic data remains blocked until the generator, truth manifest
  and limitations pass verification (Plan 4).
