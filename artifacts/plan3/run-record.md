# Plan 3 Run Record — route-c-p3-20260717

> Started 2026-07-17 after Ross's spend-preflight approval (recorded in
> `cloud/gcp/plan3/run-config.yml`). Every entry is dated; nothing here is
> restated later — corrections append.

## 2026-07-17 — preflight and provisioning

- **Approval:** spend preflight approved by Ross in chat (£10 ceiling, 80%
  stop); recorded with approver/date; mechanical guard open.
- **Auth:** authenticated as the project owner (`gcloud auth list`); the
  gcloud default project (unrelated) was left untouched — every command uses
  explicit `--project_id=neobank-growth-platform-ross`.
- **Identity decision:** the bounded run uses the authenticated owner identity
  with no service-account keys minted (fewer credentials at rest than the
  planned deployment SA; deviation from "separate identities where possible"
  recorded here). The read-only Looker service account is created only at the
  Looker stage, where its connection requires one.
- **Live inventory:** recorded in `cloud/gcp/plan3/resource-inventory.md`.
  Key finding: **billing disabled** (sandbox mode) — MERGE probe failed with
  "DML queries are not allowed in the free tier" (probe table deleted).
  Incremental benchmark blocked until billing is enabled; Ross opted to enable
  billing (console action, his own).
- **Datasets provisioned** (free; within approved scope): the five
  `neobank_p3_*_route_c_p3_20260717` datasets in `europe-west2`, labels
  `route_c: plan3` + `run: route-c-p3-20260717`, default table expiry 30 days.
  Verified via `bq ls --filter="labels.route_c:plan3"`.
- **Job attribution verified:** the labelled probe query ran under
  `--label=route_c:plan3` before the benchmark, satisfying Plan 3 §7.1's
  attribution test.
- **Standard profile:** generated and determinism-verified locally
  (568,789 deliveries / 356 batches / 312.6 MB; identical logical checksum
  `7fb8b85813d7d182…` across two runs). Local loader run into
  `data/warehouse-standard/` for Parquet upload (loads are free).

## 2026-07-17 — standard profile loaded and reconciled (Task 3)

- Local loader over the standard profile: 356 batches, 565,960 valid,
  2,829 quarantined (matches the 0.5% malformed rate).
- Consolidated Parquet (88.9 MB deliveries + 0.4 MB quarantine) batch-loaded
  into `neobank_p3_raw_route_c_p3_20260717.raw_event_deliveries` /
  `.raw_event_quarantine` — loads are free.
- **Source reconciliation exact on all checks**
  (`artifacts/plan3/source-load-manifest.json`): total 568,789; unique
  idempotency keys 560,360; duplicates 5,600; quarantined 2,829; event_ids
  unique. Cloud source state equals the local run manifest.
- Remaining stages (dbt builds, F-vs-I benchmark) blocked on billing
  enablement (sandbox blocks DML); watch armed.

## 2026-07-17 — billing enabled; benchmark phases armed (Tasks 4–5 start)

- Ross linked billing account `01C196-FFCF87-70548B`; `billingEnabled: True`
  verified; a labelled MERGE probe now **succeeds** (DML unblocked); probe
  table deleted.
- 16 legacy raw tables batch-loaded (free) into the Plan 3 raw dataset for the
  current-graph rerun, alongside the two event tables.
- dbt now stamps every BigQuery job with the invocation/node ids
  (`query-comment: job-label: true`) — attribution verified earlier with the
  labelled probe.
- **Phases pre-registered before any output** (`artifacts/plan3/phase-manifest.json`):
  90/9/1 by delivery count over `ingested_at`; Base cutoff
  `2026-05-07T04:39:31Z` (509,364 deliveries = 90.0%), Delta cutoff
  `2026-06-07T00:26:47Z`. Raw tables renamed `*_all`; the dbt sources read
  phase views so phase advances are pure view DDL.
- **Contractual dry runs recorded:** full delivery-view scan 274.4 MB;
  largest legacy source (transactions) 5.9 MB — every stage far under the
  1 GiB per-query cap; whole-build totals in single-digit GB (free tier).
- Baseline (`neobank_p3b_20260717_*`) full build launched on the Base phase.

## Spend log

| Date | Action | Bytes billed | Est. cost | Cumulative |
|---|---|---|---|---|
| 2026-07-17 | Dataset creation ×5, probe CTAS (sandbox, no billing possible) | 0 | £0.00 | £0.00 |
| 2026-07-17 | Parquet batch loads ×2 (loads are free) | 0 | £0.00 | £0.00 |
| 2026-07-17 | Source reconciliation count queries ×3 (~90 MB scans, sandbox free tier) | 0 | £0.00 | £0.00 |
