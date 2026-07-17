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

## Spend log

| Date | Action | Bytes billed | Est. cost | Cumulative |
|---|---|---|---|---|
| 2026-07-17 | Dataset creation ×5, probe CTAS (sandbox, no billing possible) | 0 | £0.00 | £0.00 |
