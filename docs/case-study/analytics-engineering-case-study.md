# Case study: a governed event warehouse, and an honest cost benchmark

> Independent, synthetic. No affiliation with Monzo or any bank; their public
> engineering writing shaped which problems I picked, not how any of it is
> built. Every number traces to [`evidence/registry.yml`](../../evidence/registry.yml).

## The question

Can a data team take duplicated, late, reversed and schema-evolving backend
events and turn them into Growth and referral-reward interfaces people can
trust — and show that an incremental warehouse gives the same answer as a full
rebuild at a cost you can actually measure? And can it do that without inventing
an unbounded bank or overselling what got built?

## Where it started

The repository began as a batch-sourced data-science portfolio: entity tables
generated directly, with solid experimentation and responsible-growth work on
top. That framing hid the hard part. Late arrivals, duplicate deliveries,
corrections, reversals, malformed payloads, schema changes — none of them
existed in the data, so nothing could show it handled them. I needed a source
where those problems are real and the correct answer is already known.

## Why I kept synthetic truth instead of switching to real data

Customer-level neobank data is private, and a real slice would not carry the
embedded ground truth that causal and reconciliation methods need to be checked.
So the core stayed synthetic — but I tightened the contract around it. Every
scenario declares a truth manifest, and results are split three ways:
engineering truth (exact, manifest-known), method validation (recovery against
seeded truth and two real public datasets), and illustrative magnitude (never
evidence about real customers). Generation and analysis stay separate, and the
non-circularity is tested.

## The event contracts

Every event shares one versioned envelope — `event_id`, `idempotency_key`,
`occurred_at`/`emitted_at`/`ingested_at` in UTC, `schema_version`, `payload` —
with money in integer minor units. Twelve event types across six locked families
validate against a JSON-Schema registry. Before generating any volume, I
hand-built a known-truth fixture with the difficult cases and their exact totals:
a duplicate delivery, a late arrival, a reversal, a malformed payload sent to
quarantine, and a deliberately missing posting. That proved the contracts could
express the hard cases first. The standard profile then generates 568,789
deliveries deterministically — two independent runs produced the same logical
checksum.

## Four layers, and interfaces that are actually governed

Models run `landing → normalised → logical → presentation`. Landing flattens
payloads, keeps ingestion metadata, deduplicates and quarantines. Normalised
builds canonical, version-independent events and current state — this is where a
v1 and a v2 referral schema become one meaning. Logical publishes four governed
interfaces, each with one owner and one authoritative grain, enforced against the
real dbt manifest by a standards checker. Existing analytics reach the interfaces
through compatibility views — the Welch/CUPED/SRM estimators behind the
experiments view run unchanged on governed data — so validated work was
preserved, not rewritten, and nothing was deleted.

## Incremental correctness and reward reconciliation

Incremental selection keys on `ingested_at`; business-state ordering keys on
`occurred_at`. The two are never conflated. A three-day ingestion lookback
repairs ordinary late arrivals; anything older needs an explicit, logged
backfill. A blue/green harness builds the same final state both ways, full
refresh and chronological incremental, and compares row counts, content
fingerprints and integer money at every interface with zero tolerance. The
referral-reward subledger books double-entry journals over three fictional
accounts — an illustrative treatment, not any real bank's policy — and
reconciles daily: debits equal credits, opening plus movements equals closing,
and every injected exception shows up with its reason code.

## The BigQuery benchmark, and its actual result

Once Gate 0 and the local platform were accepted, the warehouse executed on
BigQuery under a £10 cap with a 1 GiB per-query limit and an 80%-of-cap stop.
The Base, Delta and Repair phases (90/9/1 by ingestion) were fixed before any
output was seen. Full and incremental builds matched exactly at all six
interfaces, every phase.

The cost result is mixed, and I report it as measured. Across three repetitions,
incremental billed 1.483 GB against 1.454 GB for a full rebuild — 1.95% more —
while using 62.7% less compute (median slot-ms 765,826 versus 2,172,197). The
byte figure is not something to explain away: the raw event store is
unpartitioned, so every strategy scans the whole landing view. The ablation
isolates where byte savings live — the same seven-day reconciliation query
scanned 523.9× fewer bytes on partitioned storage. Full refresh stays the
simpler, justified choice for the raw-scan parts; incremental's win here is
compute, and partitioning is what buys bytes. Nothing is extrapolated to
production or Monzo scale. The whole run was 844 attributed jobs billing
32.99 GB, about £0.21, likely £0 under the free tier.

## What the scale run caught that the small one didn't

The repair phase held back a busy ingestion day, confirmed the ordinary lookback
missed it, and recovered it with a bounded backfill. At 569k deliveries it also
surfaced two staleness bugs the tiny-scale proof could not. A settlement that
arrived before its late-redelivered booking left an unresolved reference, and
its ledger lines stayed stale after the reference healed. I fixed both with
self-healing re-selection clauses and two new invariants, checked on DuckDB and
BigQuery, and parity came back exact on the full dataset. The failure and the
recovery are both kept as evidence.

## Looker: what I built, and the gap

There is a full LookML project — model, four Explores, three dashboards, Assert
tests — against the governed BigQuery interfaces. It never ran in a Looker
instance: the trial signup returned a sales-contact page with no instance. I
claim no Looker execution or experience; the LookML sits at "written", and the
record carries a dated upgrade path if a real no-cost trial appears.

## Trade-offs and the routes I turned down

Route B — keeping batch sources — was the explicit fallback and never fired,
because the event boundary reproduced the core inputs without an unbounded bank.
Kafka and streaming were out: this proves warehouse-side correctness, not
transport. I did not use a dbt Semantic Layer, and I do not claim one. And I
forbade one-commit model renames in favour of compatibility views.

## Limitations, and what would change in a real organisation

The data is synthetic and built for coverage, not calibrated to any population;
the accounting is illustrative; the benchmark is one dataset size, one region,
one day. A real deployment would add production identity and access controls,
data governance and retention, keyless CI/CD, a model and feature registry, and
formal Consumer Duty and model-risk approval before any live customer
decisioning. It would also partition the raw event store — which this benchmark
shows is where the byte savings are.
