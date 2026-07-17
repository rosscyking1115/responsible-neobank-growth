# Release Checklist — v1.0.0

> Gates before tagging. Publication actions (Hugging Face upload, GitHub tag)
> require the user's explicit approval; nothing here publishes on its own.

## Automated (must pass)

- [x] Full local suite green (`uv run pytest` — 494 passed)
- [x] Lint clean (`uv run ruff check .`)
- [x] Clean-clone reproduction without cloud credentials (`artifacts/plan4/reproducibility.md`)
- [x] Claim audit clean (`tools/release/claim_audit.py` — 0 findings, 54 surfaces)
- [x] Privacy/secret scan clean (`tools/release/privacy_scan.py`)
- [x] Dataset package validates (`tests/evidence/test_dataset_package.py`)
- [x] Evidence registry validates and covers all claim groups (`tests/evidence/test_registry.py`)
- [x] Release-candidate check (`tools/release/release_check.py`) — run on a clean tree

## Manual (before requesting approval)

- [x] README leads with the AE identity and achieved-evidence status
- [x] Scheduled-jobs documentation contradiction resolved with dated history
- [x] Looker described as authored/configured, never validated
- [x] Benchmark result stated as measured, mixed, with formulas and pricing date
- [x] Licence: code MIT; dataset CC-BY-4.0 (proposed; confirm at publication)
- [x] No credentials, billing IDs, private project IDs or signed URLs in artifacts
- [x] Version bumped to 1.0.0

## User-gated publication steps (do not perform without approval)

- [ ] **Approve the public diff** for v1.0.0 (this branch vs `main`)
- [ ] **Hugging Face dataset publish** — upload the built `standard` + `tiny`
      tree, verify the data card, viewer and programmatic load, record the
      immutable revision (Plan 4 Task 7)
- [ ] **GitHub release** — merge to `main`, tag `v1.0.0`, publish the release
      notes (Plan 4 Task 11)
- [ ] Optional **Kaggle mirror** after the HF release passes (Plan 4 Task 8)

## Post-release (Plan 4 Task 12)

- [ ] Clean-clone at the tag; dataset load via public API; quick start; link
      check; confirm no unintended cloud/Looker resources remain
- [ ] Record the post-release verification and freeze maintenance scope
