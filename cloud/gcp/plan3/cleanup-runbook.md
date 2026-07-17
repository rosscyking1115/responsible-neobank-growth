# Plan 3 Cleanup Runbook

> Reviewed 2026-07-17 before any provisioning (Plan 3 §5.4). Every command is
> scoped to the labelled Plan 3 resources; nothing here touches datasets,
> service accounts or jobs outside the `route_c: plan3` label and the
> `neobank_p3_*_route_c_p3_20260717` names. `purge`-style deletions run only at
> or before the cleanup deadline (2026-08-16) after evidence capture.

## Verify scope first (read-only)

```bash
bq ls --project_id=neobank-growth-platform-ross --format=prettyjson \
  | grep -i "neobank_p3_"
gcloud iam service-accounts list \
  --project=neobank-growth-platform-ross \
  --filter="displayName:route-c-p3"
```

## Evidence capture before deletion

- [ ] Export `INFORMATION_SCHEMA.JOBS` extract for the run window into
      `artifacts/plan3/` (bytes, billed bytes, slot ms, labels)
- [ ] Confirm benchmark artifacts, validator outputs, screenshots and the
      walkthrough are committed/retained (Plan 3 §14.3)
- [ ] Confirm no artifact contains credentials, billing identifiers or signed URLs

## Dataset deletion (after evidence capture)

```bash
for ds in neobank_p3_raw_route_c_p3_20260717 \
          neobank_p3_baseline_route_c_p3_20260717 \
          neobank_p3_optimised_route_c_p3_20260717 \
          neobank_p3_looker_route_c_p3_20260717; do
  bq rm -r -f --project_id=neobank-growth-platform-ross "$ds"
done
# Evidence dataset: retain ONLY if free and useful, else delete it too:
# bq rm -r -f --project_id=neobank-growth-platform-ross neobank_p3_evidence_route_c_p3_20260717
```

(Datasets also carry a 30-day default table expiry as defence in depth.)

## Identities and credentials

```bash
gcloud iam service-accounts keys list \
  --iam-account=route-c-p3-dbt@neobank-growth-platform-ross.iam.gserviceaccount.com
# revoke every key created for this run, then delete the accounts:
gcloud iam service-accounts delete \
  route-c-p3-dbt@neobank-growth-platform-ross.iam.gserviceaccount.com --quiet
gcloud iam service-accounts delete \
  route-c-p3-looker@neobank-growth-platform-ross.iam.gserviceaccount.com --quiet
```

## Looker trial

- [ ] Disable schedules and any public links
- [ ] Export permitted LookML/evidence
- [ ] Delete the trial instance or record its expiry date and non-conversion
- [ ] Confirm no payment method was attached

## Final audit

- [ ] `bq ls` shows no `neobank_p3_*` datasets beyond an intentionally retained
      evidence dataset (recorded with reason)
- [ ] No scheduled queries or transfers exist for the project from this run
- [ ] Final job inventory reconciled against the benchmark report
- [ ] Cleanup recorded in `artifacts/plan3/resource-cleanup.md`
