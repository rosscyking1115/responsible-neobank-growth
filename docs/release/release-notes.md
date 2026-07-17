# Release Notes — v1.0.0 (Route C)

> **Draft — not published.** Tagging and publishing require explicit user
> approval (Plan 4 §13.1). Release branch: **BigQuery-only**.

First stable release. Route C reframed the project from a batch-sourced
data-science portfolio into a governed **event-to-interface Analytics
Engineering platform**, verified end to end through four gated plans.

## What is implemented and verified

- **Deterministic event simulator** — versioned envelope, six source families,
  injected failure scenarios, virtual clock; 568,789-delivery `standard` profile
  reproduces an identical logical checksum across runs.
- **Append-only ingestion** — checksum-gated batch registry, idempotent replay,
  quarantine-as-evidence with conflicting-duplicate detection.
- **Four-layer dbt warehouse** — `landing → normalised → logical → presentation`,
  incremental event models, contracts, unit tests; four governed interfaces with
  standards enforced against the real manifest.
- **Referral-reward subledger** — double-entry over fictional accounts,
  daily reconciliation, exact exception detection.
- **Incremental correctness** — blue/green harness proves exact full-vs-incremental
  parity; bounded backfill for beyond-lookback arrivals.
- **BigQuery benchmark (executed)** — 68 models / 215 tests on BigQuery; exact
  parity at every phase; **measured** cost (incremental +1.95% bytes / −62.7%
  compute; 523.9× ablation) for ~£0.21 under a £10 cap.
- **LookML semantic layer (authored/configured)** — model, four Explores, three
  dashboards, Assert tests; **not** validated (trial access-limited).
- **Synthetic event benchmark dataset** — packaged with truth manifests,
  schemas, checksums and a data card (release pending approval).

## Migration / deprecation notes

- Existing analytics reach the new governed interfaces through **compatibility
  relations**; legacy relations still build. No model was deleted; the
  compatibility name-swap is gated on per-consumer verification.
- The four-layer models are additive; the previous staging/intermediate/mart
  graph is preserved as downstream consumers.

## Benchmark environment and result (concise)

BigQuery `europe-west2`, 569k-delivery synthetic profile, three repetitions,
2026-07-17. Incremental vs full rebuild: exact interface parity; +1.95% bytes,
−62.7% median slot-ms. Partitioning ablation: 523.9× fewer bytes for one query.
Full absolute values: `artifacts/plan3/benchmark-summary.json`. No extrapolation
to production or Monzo scale.

## Looker validation status

Authored and reviewed, **not validated in a Looker instance** — the trial was
access-limited. No Looker experience is claimed. Upgrade path recorded if a
genuine no-cost trial is provisioned before the cleanup deadline.

## Known limitations and unresolved issues

- Synthetic data engineered for oracle coverage, not calibrated to any bank.
- Cost result is mixed and reported as measured; byte parity is a property of
  the unpartitioned raw store.
- Interface-manifest ↔ dbt-meta alignment is reviewed manually (mechanical
  cross-check deferred).
- Standard dataset is built on demand, not committed.

## Reproducibility and cleanup

- Clean-clone local reproduction verified without cloud credentials
  (`artifacts/plan4/reproducibility.md`).
- Cloud resources retained until 2026-08-16 with auto-expiry backstops, then
  deleted per `cloud/gcp/plan3/cleanup-runbook.md`.

## Affiliation

Independent, synthetic, **not affiliated** with Monzo or any bank.
