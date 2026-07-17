# Route C — Plan 2 Verification Summary

> **Date:** 2026-07-17 · **Branch:** `feat/route-c-plan2-warehouse` (12 commits on
> the accepted Plan 1 branch) · **Decision:** **go-to-plan-3** (pending user
> acceptance; Plan 3 additionally requires its own spend preflight approval)
> Machine-readable gates: [verification-results.json](verification-results.json)

## What Plan 2 built

Deterministic versioned service events now enter a four-layer dbt warehouse;
duplicates, late arrivals, reversals, malformed payloads, schema evolution,
freshness outages and reconciliation breaks are handled according to the frozen
Gate 0 rules; governed Growth and reward-reconciliation interfaces reproduce
exact known truth and serve approved existing consumers through declared
compatibility contracts.

- **Simulator:** seeded, virtual-clock generation across all six locked
  families; fault injection layered after valid generation so truth stays
  separable; two independent runs produce byte-identical batches
  (1,833 deliveries, 72 daily batches on the tiny profile).
- **Ingestion:** append-only per-batch Parquet with checksum verification,
  idempotent batch registry, and evidence-preserving quarantine including
  conflicting-duplicate detection at high severity.
- **Warehouse:** 9 landing + 11 normalised + 5 logical + 5 presentation +
  4 compatibility models; 8 event-grain models are incremental
  (delete+insert locally, merge on BigQuery) with the frozen 3-day ingestion
  lookback; state/interface models carry documented exemptions.
- **Blue/green proof:** full-refresh and chronological-incremental builds reach
  **exact parity** at 6 governed interfaces (zero tolerance on keys and
  financial integers); same-batch replay is a no-op; a held-back old-ingestion
  batch is demonstrably missed by the ordinary lookback and recovered by the
  explicit bounded backfill with recorded reason and operator
  ([blue-green-report.json](blue-green-report.json), [backfill-log.jsonl](backfill-log.jsonl)).
- **Subledger:** double-entry journal over the three fictional accounts; daily
  reconciliation with append-only reason codes; the built warehouse matches the
  generation manifest exactly (entitlements, ledger totals, exception
  identities, lifecycle states).
- **Preservation:** the anchor consumer — the Welch/CUPED/SRM estimators behind
  the Experiments tab — runs unchanged on `cmp_fct_experiment_user_metrics`,
  which is served entirely from governed interfaces. Legacy models still build
  untouched; nothing was deleted.
- **Standards:** the checker now enforces owner/purpose/grain/unique-key/
  freshness/classification/version/compatibility/exposures/partition-policy on
  every `nrm_`/`lgl_` model in the **real** dbt manifest, in CI.
- **BigQuery readiness:** partition/cluster/label configs and adapter-aware
  merge strategy are in place; `dbt parse --target bigquery` validates
  statically with a dummy project id. **Configured, not executed** — no cloud
  charge occurred; correctness on BigQuery remains unverified until Plan 3.

## How to reproduce

```bash
uv run python -m tools.ci.verify_plan2
```

runs lint, the full pytest suite, double generation with checksum comparison,
loading, the full dbt build, standards enforcement, the blue/green harness and
the pipeline-gated tests, then fails if any truth/reconciliation artifact is
missing. CI (`.github/workflows/ci.yml`) runs the same stages on every push.

## Gate results

All nine mandatory gates (P2.1–P2.9) **pass** with evidence paths recorded in
[verification-results.json](verification-results.json).

## Open items carried forward (not hidden)

1. The **standard profile (1M deliveries) has not been generated yet** — its
   first full run and runtime measurement belong to Plan 3 preflight, and the
   generator's per-event schema validation likely needs a validator cache
   before that run is practical.
2. Interface-manifest ↔ dbt-meta alignment is manually reviewed; a mechanical
   cross-check is deferred.
3. Compatibility relations run **in parallel** with the legacy relations; the
   name swap waits for per-consumer verification (removal gate declared in
   `compatibility.yml`).
4. Plan 4 still owes a clean-clone reproduction on a fresh machine.

## What Plan 2 did not do (by design)

No Looker trial or Looker claims; no BigQuery execution, performance or cost
statements; no public dataset release; no Kafka/streaming; no rewrite of
Streamlit/API/ML internals; no deletion of existing models or evidence.
