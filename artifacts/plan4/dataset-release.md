# Canonical Dataset Release — Hugging Face (Plan 4, Task 7)

> **Published and verified 2026-07-17.**

- **Repository:** <https://huggingface.co/datasets/rosscyking/responsible-neobank-growth-events>
- **Type:** dataset, public
- **Commit revision:** `0111c26e4b106f5769996a5fc5256132e80ef93e`
- **Licence:** CC-BY-4.0 (data); MIT (code, in the source repository)
- **Contents:** tiny + standard profiles (568,789 + 1,833 deliveries), truth
  manifests, schemas, configs, checksums, data card, `validate_truth.py` —
  313.5 MB, 451 files.

## Verification from a clean download

Downloaded the published repository to an isolated directory and checked it
against the shipped manifests:

- `examples/validate_truth.py tiny` → **PASS**
- `examples/validate_truth.py standard` → **PASS**
- SHA256SUMS: **449 files checked, 0 mismatches**
- Downloaded size 313.6 MB, 356 standard batches present — the data
  transferred intact (the uploader's "0.00B" counter is a dedup-backend display
  quirk, not a missing-data signal).

## Provenance

Built by `tools/release/build_dataset.py --profiles tiny standard` from the
deterministic generator at the v1.0.0 source commit; data files are generator
output, never hand-edited. The standard profile reproduces the logical checksum
`7fb8b85813d7d182…` across independent runs.

## Cleanup note

The Hugging Face write token created for this upload
(`route-c-dataset-publish`) can be revoked at
<https://huggingface.co/settings/tokens> now that the publish is complete.
