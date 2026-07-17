# Case Study: A Governed Event-to-Interface Warehouse with a Measured Cost Benchmark

> Independent, synthetic reference project. No affiliation with Monzo or any
> bank; Monzo's public engineering writing informed the problem framing, not any
> internal implementation. Every number here resolves to
> [`evidence/registry.yml`](../../evidence/registry.yml).

## 1. The question

Can a data team turn duplicated, late, reversed and schema-evolving backend
events into trusted Growth and referral-reward interfaces, and prove that an
incremental warehouse produces the same truth at a measured cost — without
inventing an unbounded banking system or overstating what was built?

## 2. Where this started

The repository began as a batch-sourced data-science portfolio: entity tables
generated directly, with strong experimentation and responsible-growth
methodology on top. That framing hid the hard analytics-engineering problems —
late arrivals, duplicate deliveries, corrections, reversals, malformed payloads
and schema evolution had no representation, so no model could demonstrate it
handled them. The project needed a source boundary where those problems exist
and where the correct answer is known exactly.

## 3. Why synthetic known truth was kept, not replaced

Customer-level neobank data is private, and a real slice would not carry the
embedded ground truth needed to validate causal and reconciliation methods. So
the core stayed synthetic — but the synthetic contract was made stricter: every
scenario declares a truth manifest, and results are separated into engineering
truth (exact, manifest-known), analytical method validation (recovery against
seeded truth and two real public datasets), and illustrative business magnitude
(never evidence about real customers). Generation and analysis are kept
separate and the non-circularity is tested.

## 4. Event contracts and failure scenarios

Every event shares one versioned envelope (`event_id`, `idempotency_key`,
`occurred_at`/`emitted_at`/`ingested_at`, `schema_version`, `payload`, …) with
currency in integer minor units and UTC timestamps. Twelve event types across
six locked families are validated against a JSON-Schema registry. A hand-built
"known-truth" fixture encodes the difficult cases with exact expected totals —
duplicate delivery, late arrival, reversal, malformed-to-quarantine, and an
intentionally missing posting — so the contracts were proven expressive before
any volume existed. The standard profile then generates 568,789 deliveries
deterministically (identical logical checksums across two independent runs).

## 5. Four layers and governed interfaces

Models are `landing → normalised → logical → presentation`. Landing owns
payload flattening, ingestion metadata, deduplication and quarantine; normalised
owns canonical version-independent events and SCD2/current state; logical owns
governed cross-entity interfaces; presentation owns replaceable consumer shapes.
Only normalised and logical become governed interfaces, each with one
authoritative grain, one owner, freshness SLOs and a compatibility policy,
enforced against the real dbt manifest by a standards checker. Existing
analytics reach the interfaces through **compatibility relations** — the
Welch/CUPED/SRM estimators behind the experiments view run unchanged on governed
data — so validated capability was preserved, not rewritten, and nothing was
deleted.

## 6. Incremental correctness and reward reconciliation

Incremental selection keys on `ingested_at`; business-state ordering keys on
`occurred_at` — never conflated. A three-day ingestion lookback repairs
ordinary late arrivals; anything older needs an explicit, logged bounded
backfill. A blue/green harness builds the same final event set two ways —
full refresh vs chronological incremental — and compares row counts, content
fingerprints and integer financial totals at every governed interface, with
zero tolerance for keys and money. The referral-reward subledger books
double-entry journals over three fictional accounts (an illustrative treatment,
not any real bank's policy) and reconciles daily: debits equal credits, opening
plus movements equals closing, and every injected exception surfaces with its
reason code.

## 7. The BigQuery benchmark and its actual result

After Gate 0 and the local platform were accepted, the warehouse executed on
BigQuery under a preflight-approved £10 ceiling with a 1 GiB per-query cap and an
80%-of-ceiling stop. Base/Delta/Repair phases (90/9/1 by ingestion) were
registered before any output was inspected. Full and incremental lineages
reached **exact parity** at all six governed interfaces at every phase.

The cost result is **mixed, and reported as measured**: across three
repetitions, incremental processing billed 1.483 GB versus 1.454 GB for a full
rebuild (**+1.95%**) while using **62.7% less compute** (median slot-ms 765,826
vs 2,172,197) at comparable runtime. The byte parity is not a failure to explain
away — the raw event store is unpartitioned, so every strategy scans the full
landing view. The physical-design ablation isolates where byte savings actually
come from: the identical seven-day reconciliation query processed **523.9× fewer
bytes** on partitioned versus unpartitioned storage. Full refresh remains the
simpler, justified choice at this scale for the parts that scan the raw store;
incremental's win here is compute, and partitioning is what unlocks byte
savings. Nothing is extrapolated to production or Monzo scale. The whole run
was 844 attributed jobs billing 32.99 GB ≈ £0.21 (likely £0 under the monthly
free tier).

## 8. What the scale run caught that the small one did not

The repair phase held back a busy ingestion day, confirmed the ordinary lookback
missed it, and recovered it with a bounded backfill. At 569k-delivery scale this
also exposed two real staleness defects the tiny-scale proof could not: a
settlement that arrived before its (late-redelivered) booking froze an
unresolved reference, and its ledger lines stayed stale after the reference
healed. Both were fixed with self-healing re-selection clauses and two new
invariants, verified on DuckDB and BigQuery, after which parity was exact on the
complete dataset. The failure-and-recovery evidence is retained.

## 9. Looker: what was built, and the honest gap

A complete LookML project — model, four Explores, three dashboards, Assert tests
— is authored against the governed BigQuery interfaces. It was **not** validated
in a Looker instance: the trial signup returned a sales-contact outcome with no
instance provisioned. No Looker execution or experience is claimed; the LookML
stands at "configured", and the record carries a dated upgrade path if a genuine
no-cost trial is later provisioned.

## 10. Trade-offs and rejected routes

- **Route B (keep batch sources)** was kept as an explicit fallback and never
  triggered — the event boundary reproduced the core inputs without an unbounded
  bank system.
- **Kafka/streaming** was excluded: the project proves warehouse-side
  correctness, not transport.
- **A dbt Semantic Layer** was not adopted; governed dbt marts/interfaces are
  used and no Semantic Layer usage is claimed.
- **One-commit model renames** were forbidden in favour of compatibility
  relations.

## 11. Limitations and what would differ in a real organisation

The data is synthetic and engineered for oracle coverage, not calibrated to any
real population; the accounting treatment is illustrative; the benchmark is one
dataset size in one region on one day. A real deployment would add production
identity and access controls, data governance and retention, keyless CI/CD, a
model/feature registry, and formal Consumer Duty and model-risk approval before
any live customer decisioning — and would partition the raw event store, which
this benchmark shows is where the byte savings live.
