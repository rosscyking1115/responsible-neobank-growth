# Incremental Correctness Contract

> **Status:** Accepted 2026-07-17 (Plan 1, Task 7). Freezes the semantics Plan 2
> must implement and Plan 3 must measure. Oracle behaviour is executable now:
> `tests/oracles/test_incremental_oracle_spec.py` proves the tiny fixtures
> distinguish full truth from dropped-late-event and duplicate-counting failures.

## Processing boundary

- **Incremental selection uses `ingested_at`** (warehouse arrival time).
- **Business-state ordering uses `occurred_at`** plus deterministic tie-breakers
  (`event_id` ascending).
- The two must never be conflated: a late event is *selected* by its arrival
  partition but *ordered* by its business occurrence.

## Watermark and lookback

- Default lookback: a **3-day** ingestion lookback (an operational policy for this
  benchmark, not a universal banking recommendation). Gate 0 adopts this value;
  Plan 2 implements it.
- Plan 2 fixtures must include a delivery at **2 days 23 hours** (recovered by the
  ordinary lookback) and one at **3 days 1 hour** (requiring explicit bounded
  backfill). The Plan 1 `late-arrival` fixture exercises the inside-lookback case
  at 48 hours.
- A pipeline that silently drops arrivals beyond its watermark produces fewer
  canonical events and less entitlement than the truth manifest — the oracle
  detects exactly this (`test_oracle_detects_dropped_late_events`).

## Idempotency

Running the same batch twice must not change:

- canonical event counts;
- entity current states;
- reward entitlements or balances;
- presentation metrics;
- reconciliation exception counts.

Delivery-layer counts may reflect repeated delivery only if the loader contract
explicitly retains it; canonical outputs may never double-count
(`test_oracle_detects_duplicate_counting`).

## Bounded backfill

- A backfill accepts a bounded ingestion/event date range, records reason and
  operator, and rebuilds only the necessary partitions/state.
- An unbounded full refresh is a separate, named recovery path — never silently
  triggered by a backfill command.

## Blue/green comparison

For every mandatory scenario, Plan 2 must:

1. build a clean full-refresh reference in an isolated schema/database;
2. build the same final event set through chronological incremental batches;
3. compare row counts, keys and content hashes at governed interfaces;
4. allow differences only for run metadata declared non-semantic;
5. emit a machine-readable reconciliation artifact.

**No tolerance** is allowed for integer financial values or exception
identities. Numerical analytical measures require an explicit precision/tolerance
contract before any difference is accepted.

## Freshness

Source freshness is declared per interface (`contracts/interfaces/*.yml`,
`freshness_slo`). An arrival gap beyond the threshold is an SLO failure that the
`warehouse_health` interface must surface; reporting a stale source as fresh is a
detected oracle failure (`test_oracle_detects_missed_freshness_outage`).
