# Clean-Environment Reproducibility (Plan 4, Task 2)

> **Result: PASS** — a fresh clone of the release branch reproduces the full
> local platform end to end with **no cloud credentials**, on 2026-07-17.

## Method

1. `git clone --branch feat/route-c-plan4-release --single-branch <repo>` into
   an isolated scratch directory (no shared `raw/`, `data/`, `.venv`, or dbt
   target).
2. `uv run python -m tools.ci.verify_plan2` from the clean checkout.

## Result

All ten stages passed (`clean-clone-verification.json`): lint, unit tests,
deterministic generation ×2 with checksum comparison, batch-raw generation,
event load, DuckDB dbt build, standards-as-code, blue/green interface parity,
and the pipeline-gated tests. Blue/green parity held. No missing artifacts.

## What this caught (Plan 4 §6.3 in action)

The first clean run **failed at dbt-build**: the legacy graph reads the batch
generator's output (`raw/ci`), which the developer working tree happened to
have but a fresh clone does not, and `verify_plan2` did not generate it. This
is exactly the "broken default path blocks release" gate — fixed by adding the
`generate-batch-raw` stage (`dc75a24`), after which the clean clone passed.

## Reproducibility contract satisfied

- dependency lockfile (`uv.lock`) drives the environment;
- no command depends on uncommitted local files;
- fixed seeds/config hashes produce identical `tiny` logical checksums;
- no current-date dependency (virtual clock throughout);
- a fresh user runs `tiny` and the full local proof **without cloud
  credentials** — cloud and Looker are optional evidence paths, not
  prerequisites for local use.

## Scope note

This exercises the **local** platform (Plan 4 §6.1 environment 1). The
BigQuery evidence (Plan 3) and the public-dataset consumer path (Plan 4 Task 7,
if the dataset is released) are separate reproducibility environments recorded
with their own artifacts.
