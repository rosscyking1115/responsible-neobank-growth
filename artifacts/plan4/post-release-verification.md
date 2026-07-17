# Post-Release Verification (Plan 4, Task 12)

> **Result: PASS.** Verified 2026-07-17 against the published v1.0.0 release and
> the live Hugging Face dataset.

## GitHub v1.0.0

- Release live: <https://github.com/rosscyking1115/responsible-neobank-growth/releases/tag/v1.0.0>
- Tag `v1.0.0` points at the merged `main` commit `cdd6bfe`.
- **Fresh clone of the tag from GitHub** (not the working tree):
  - 72 tiny dataset batches present (the earlier gitignore bug is fixed in the
    release);
  - quick start runs — `generate` tiny twice, `compare` reports *outputs are
    logically identical*;
  - every local README link resolves — no broken links.
- The dataset link (README badge + results row) was added after the tag on
  `main` (`2fdd71b`); the tag itself is the immutable release and does not carry
  it, which is expected.

## Hugging Face dataset

- Published and verified from a clean download (see
  [dataset-release.md](dataset-release.md)): `validate_truth` PASS for tiny and
  standard; 449 checksummed files match; 313.6 MB, 356 standard batches.
- Revision `0111c26e`, CC-BY-4.0.

## Cloud and Looker resources

- Five labelled `neobank_p3_*_route_c_p3_20260717` datasets remain, as recorded
  in [resource-cleanup.md](../plan3/resource-cleanup.md): retained until
  **2026-08-16** for the possible Looker trial, ~2 GB inside the 10 GB free
  storage tier (£0), with a 30-day table-expiry backstop.
- No Looker instance exists (the trial was access-limited). No service-account
  keys were minted. No scheduled queries or transfers from this run.
- Billing is now enabled on the project (linked for the benchmark); the retained
  datasets are storage-only within the free tier, so they carry no ongoing
  charge. Deletion at or before the deadline per the cleanup runbook.

## Outcome

All applicable Plan 4 gates pass. The four-plan programme is complete. Recorded
defects/corrections during release: the over-broad `.gitignore data/` rule that
CI caught (fixed), and a mis-targeted local commit (moved to the correct branch).
No benchmark result was altered; corrections are dated records, not rewrites.
