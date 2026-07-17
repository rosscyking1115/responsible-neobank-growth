# ADR: Route C Plan 4 decision

## Status

Accepted — 2026-07-17 (Plan 4, Task 12). Outcome recorded: **release**.
This closes the four-plan Route C programme.

## Context

Plan 4 audited every claim against retained evidence, consolidated the
repository, and published on the branch the Plan 3 result allowed
(BigQuery-only). Four outcomes were possible: `release`, `repository release
only`, `evidence freeze`, `repair required`.

## Decision

**release.** Both public surfaces are live and verified:

- **GitHub v1.0.0** — merged to `main`, tagged, released; a fresh clone of the
  tag runs the quick start and every README link resolves
  ([post-release verification](../../artifacts/plan4/post-release-verification.md)).
- **Hugging Face dataset** (CC-BY-4.0) — published and verified from a clean
  download, checksums and truth intact
  ([dataset release](../../artifacts/plan4/dataset-release.md)).

Supporting gates, all passed: the evidence registry with a mechanical claim
audit (no unanchored number, no forbidden Looker wording); clean-clone
reproduction without cloud credentials; licence, privacy and security review;
the scheduled-jobs documentation contradiction resolved with dated history; and
the reader-facing prose rewritten in the author's voice in UK English.

## Consequences

- The project is released and enters maintenance ([maintenance policy](../MAINTENANCE.md)):
  feature work is frozen; only reproducibility, security, claim-accuracy or
  dependency-break fixes proceed.
- Looker stays authored, not validated, on the BigQuery-only branch. If a genuine
  no-cost trial is provisioned before the 2026-08-16 cleanup deadline, the
  validators run and the record upgrades by dated addendum — never by rewriting.
- Retained cloud datasets are storage-only within the free tier and are deleted
  at or before the deadline per the cleanup runbook.

## No later plan re-litigates an earlier one

Each plan's acceptance stands on its own dated evidence. This ADR does not
restate or revise Gate 0, Plan 2 or Plan 3; it records that the release, the
last step, is done.
