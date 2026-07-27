---
license: cc-by-4.0
tags:
  - synthetic
  - analytics-engineering
  - data-quality
  - incremental-processing
  - reconciliation
pretty_name: Responsible Neobank Growth — Synthetic Event Benchmark
configs:
  - config_name: tiny
    default: true
    data_files:
      - split: train
        path: data/tiny/*.jsonl
dataset_info:
  - config_name: tiny
    features:
      - name: event_id
        dtype: string
      - name: idempotency_key
        dtype: string
      - name: event_name
        dtype: string
      - name: schema_version
        dtype: int64
      - name: occurred_at
        dtype: string
      - name: emitted_at
        dtype: string
      - name: ingested_at
        dtype: string
      - name: producer_id
        dtype: string
      - name: source_service
        dtype: string
      - name: trace_id
        dtype: string
      - name: scenario_id
        dtype: string
      - name: generator_version
        dtype: string
      - name: payload
        struct:
          - name: account_id
            dtype: string
          - name: amount_minor
            dtype: int64
          - name: application_id
            dtype: string
          - name: assignment_unit
            dtype: string
          - name: beneficiary_customer_id
            dtype: string
          - name: campaign_id
            dtype: string
          - name: channel
            dtype: string
          - name: currency
            dtype: string
          - name: customer_id
            dtype: string
          - name: decision
            dtype: string
          - name: decision_source
            dtype: string
          - name: experiment_id
            dtype: string
          - name: funding_method
            dtype: string
          - name: invite_channel
            dtype: string
          - name: is_first_funding
            dtype: bool
          - name: outcome_type
            dtype: string
          - name: qualification_rule
            dtype: string
          - name: qualified_reason
            dtype: string
          - name: qualifying_account_id
            dtype: string
          - name: referral_id
            dtype: string
          - name: referred_customer_id
            dtype: string
          - name: referrer_customer_id
            dtype: string
          - name: requested_product
            dtype: string
          - name: reversal_id
            dtype: string
          - name: reversal_reason
            dtype: string
          - name: reward_id
            dtype: string
          - name: settlement_id
            dtype: string
          - name: severity
            dtype: string
          - name: spend_date
            dtype: string
          - name: variant
            dtype: string
---

# Responsible Neobank Growth — Synthetic Event Benchmark

A synthetic dataset of neobank service events that misbehave on purpose — late,
duplicated, reversed, schema-evolving — with the correct answer known in
advance. It is built for testing incremental pipelines, data contracts,
referral-reward reconciliation, data quality and BI, where you want to check a
warehouse's output against a fixed truth rather than eyeball it.

> Fully synthetic. No affiliation with Monzo or any bank; no real customer,
> internal, or proprietary data. The identifiers are salted hashes, not people.
> Do not treat any of it as representative of a real population.

## What it's for

Turn messy backend events into interfaces you can trust, and check that an
incremental warehouse gives the same answer as a full rebuild. The events back
four governed questions: growth acquisition, referral economics, reward
reconciliation, warehouse health.

## What's inside

```text
data/<profile>/*.jsonl     immutable ingestion-day delivery batches (envelope + payload)
truth/<profile>-manifest.json   the exact expected outcomes (counts, duplicates, quarantine, ledger, exceptions)
schemas/                   event envelope + payload JSON Schemas + registry
configs/                   generator profile configs (seed, clock, scenario mix)
checksums/SHA256SUMS       per-file checksums
examples/validate_truth.py recompute the observable facts and check them against truth
build-manifest.json        generator version, profiles, logical checksums, licence
```

Every event shares one envelope — `event_id`, `idempotency_key`, `event_name`,
`occurred_at`/`emitted_at`/`ingested_at` in UTC, `schema_version`, `payload` —
with money in integer minor units.

### Why the schema is pinned in this card

`payload` is a union: its fields depend on `event_name`, and `referral-qualified`
appears under both `schema_version` 1 and 2 with different fields. That is the
dataset's subject matter, not an accident.

It does mean the shape cannot be inferred per file. Each day's file contains a
different mix of event types, so inferring separately gives a different `payload`
struct per file — and a field that happens to be absent from one day infers as
null, which will not merge with a string. Reading the files together then fails
with an Arrow schema-mismatch error, which is what breaks a preview.

So this card declares the full union explicitly in `dataset_info.features`: the
30 payload fields across all event types, each with one consistent type. Every
file is cast to that one schema, and a field an event does not carry reads as
null. **Do not remove this block.** Without it the dataset still downloads, but
the viewer and a plain `load_dataset` over multiple files will fail to unify the
schema. If a new event type or payload field is ever added, add it here too.

## Profiles

| Profile | Deliveries | Use |
|---|---|---|
| `tiny` | ~1.8k | contracts, CI, a quick look (shipped with the repo) |
| `standard` | ~569k | pipeline and benchmark scale (built on demand; same logical checksum across runs) |

## The injected failures

Faults go in after valid generation, so the truth stays separable from the
defects: duplicate deliveries sharing an idempotency key, late and
beyond-lookback arrivals, reward reversals, malformed payloads sent to
quarantine, v1 and v2 schemas side by side, a freshness outage, and
reconciliation breaks. `truth/<profile>-manifest.json` states the exact expected
counts, lifecycle end states, ledger totals and exception reason codes.

## Reproducibility

Seeded generators on a virtual UTC clock — no wall clock, no random UUIDs. The
same profile config reproduces the same logical content: two independent
`standard` runs gave the same logical checksum. Generator version and seeds are
in `configs/` and `build-manifest.json`.

## Validation

Recompute and compare against the truth manifest with
`examples/validate_truth.py`, plus the repository's contract, oracle and
blue/green tests. The `base`/`delta`/`repair` splits are pipeline-processing
phases, not ML train/validation/test.

## Limitations

Volumes, rates and amounts are engineered for coverage and are not calibrated to
any bank. The reward accounting is an illustrative double-entry treatment, not
any real institution's policy. Do not infer anything about real customers or
populations from it.

## Intended and prohibited uses

Use it for data-engineering teaching, incremental-pipeline and backfill testing,
reconciliation and data-quality demos, and BI or semantic-layer demos. Do not
use it for lending, fraud or AML decisions, customer profiling, regulatory
reporting, or any claim about real populations — it cannot support those and
must not be used for them.

## Licence and citation

Data: CC-BY-4.0. Code (repository): MIT © 2026 Cheng-Yuan King. Please cite the
repository and commit. No affiliation with Monzo Bank Ltd is claimed or implied.

## Provenance

Generated by the [Responsible Neobank Growth](https://github.com/rosscyking1115/responsible-neobank-growth)
project. The repository commit and per-file checksums are in
`build-manifest.json` and `checksums/SHA256SUMS`. Issues go to the repository's
tracker.
