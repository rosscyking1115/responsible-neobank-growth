# Plan 3 Spend Preflight — Approval Record

> **Status: APPROVED by Ross on 2026-07-17** (in chat, after review of the
> measured standard profile and the £10 ceiling). The mechanical gate
> `approval.spend_preflight_approved` in [run-config.yml](run-config.yml) is
> now open with approver and date recorded; the 80%-of-ceiling stop and all
> query controls remain in force.

## What approval authorises

The bounded Plan 3 BigQuery execution (Plan 3 §2.1) in project
`neobank-growth-platform-ross`, region `europe-west2`, inside the five labelled
`neobank_p3_*_route_c_p3_20260717` datasets with 30-day expiry: loading the
standard synthetic profile, rerunning the current graph, the Base/Delta/Repair
full-versus-incremental benchmark, the warehouse-health evidence mart, and the
Looker trial's validation queries. Nothing else.

## Ceiling

- **Proposed maximum incremental cash exposure: £10.** No overage authorised.
- Hard stop at **80% of ceiling** on cumulative observed/estimated spend.
- Safety mechanisms: 1 GiB `maximum_bytes_billed` per query (exceptions need a
  recorded dry run), custom query quota (200 GiB/day proposed), staged
  execution, labelled job attribution, and the shutdown checklist. **Billing
  alerts are not caps** and are not relied on.

## Pricing references (verified 2026-07-17; re-verify at execution)

- Official page: <https://cloud.google.com/bigquery/pricing> (authoritative at
  execution time — the figures below are planning references).
- On-demand analysis: **$6.25/TiB** (US baseline) after the **1 TiB/month free
  tier**; `europe-west2` (London) carries a regional premium — planning bound
  used here: **$8.75/TiB**. Exact regional rate to be read off the official
  page during Task 1 execution and recorded in the run record.
- Batch loading into BigQuery: **free** (shared slot pool). Storage free tier
  10 GB/month; our footprint (~0.1–0.5 GB) is within it and expires with the
  datasets.

## Standard profile — measured (2026-07-17, Plan 3 precondition satisfied)

- Generated locally: **568,789 deliveries in 356 daily batches, 312.6 MB raw
  JSONL**, ~13 minutes wall time after the validator-cache fix
  (`perf: precompile event schema validators`).
- Run manifest with truth, per-batch checksums and logical checksum:
  `data/generated/standard/manifest.json` (logical checksum `7fb8b85813d7d182…`).
- Determinism verified at scale on 2026-07-17: a second independent run
  produced the identical logical checksum and
  `python -m src.event_simulator.cli compare` reported
  **"outputs are logically identical"** (exit 0).
- Note: the accepted configuration (120k customers, 1M delivery cap) lands at
  ~569k deliveries — recorded as the benchmark size; no claim of 1M is made.

## Estimated usage (bases stated; dry runs will replace estimates)

These are **size-based estimates**, not dry runs. Before the first billable
query, each stage below gets a BigQuery dry run (free, no slots consumed) and
this table is re-recorded with estimated bytes; execution halts if any stage
estimate materially exceeds the planning figure.

| Stage | Basis | Estimated scan |
|---|---|---|
| Load standard profile (569k deliveries, 312.6 MB raw) | batch load | £0 (loads are free) |
| Current-graph rerun (Plan 3 §8.2) | ~50k-user batch dataset, 34 legacy relations | ~10 GB |
| Route C base build ×2 schemas (baseline + optimised) | ~0.35 GB raw scanned across ~30 models | ~25 GB |
| Delta + Repair, F and I strategies | 4 further builds + 2 incremental runs | ~50 GB |
| Performance repetitions (≤3 where budget permits) | repeat of Delta comparison | ~60 GB |
| Physical-design ablation (optional, budget-gated) | one representative query ×2 configs | ~5 GB |
| Warehouse-health mart + INFORMATION_SCHEMA extracts | metadata-priced/free-tier | ~1 GB |
| Looker validation (fixture Explores, dashboards) | bounded validation queries | ~10 GB |
| **Total (upper bound)** | | **~160 GB ≈ 0.16 TiB** |

**Expected cost: £0** if the 1 TiB monthly free tier is available on this
billing account, else ~**£1.10–£1.40** at the London planning rate — both far
inside the £10 ceiling. The 80% stop triggers at £8 observed/estimated.

## Repetitions

One mandatory correctness run per phase; performance repetitions up to three
only if cumulative estimates stay under the stop line. Every run reported
(median and range); no slow run discarded without a documented platform error.

## Billing state

Current billing account state and free-tier availability are read from the
console at execution start (not accessible from this preflight) and recorded in
`artifacts/plan3/` before the first billable query.

## Resources and deletion deadline

Exactly the five datasets in [run-config.yml](run-config.yml), all labelled
`route_c: plan3`, dataset expiry 30 days, cleanup deadline **2026-08-16**,
commands in [cleanup-runbook.md](cleanup-runbook.md) (reviewed; nothing targets
resources outside the labelled scope).

## Looker trial

Activated only after the readiness gate (docs/looker/trial-runbook.md) and only
if verified **no-cost** under the actual signup terms at activation time; any
billing requirement or auto-conversion stops the trial path and records
`partial go — BigQuery only`.

## What Ross is approving

1. The £10 ceiling and the staged execution above in the named project/region.
2. Creation of the five labelled datasets and least-privilege identities.
3. Nothing else — publication, README claims and any further spend remain
   separately gated.

**To approve:** say so in chat; the approval is then recorded in
`run-config.yml` (`approved_by`, `approved_on`) and this file's status line.
**Prerequisite for execution:** an authenticated `gcloud`/`bq` session on this
machine for the target project (credentials are never stored in the repo).
