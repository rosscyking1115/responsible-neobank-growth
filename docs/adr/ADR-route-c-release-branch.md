# ADR: Route C release branch

## Status

Accepted — 2026-07-17 (Plan 4, Task 1).

## Context

Plan 4's release adapts to the actual Plan 3 outcome. Plan 3 recorded
**partial go — BigQuery only** (user-accepted): the BigQuery benchmark passed
every applicable gate with a mixed, honestly-reported result, while genuine
Looker validation was access-limited (sales-contact outcome, no instance).

## Decision

The release proceeds on the **BigQuery-only branch** (Plan 4 §2.2):

- public wording may state that the governed warehouse **executed on
  BigQuery** and that the benchmark **measured** bytes, runtime, slot use and
  estimated cost, with the mixed result and its cause (unpartitioned raw
  store) stated plainly;
- prepared LookML is described as **authored/configured, not validated**; the
  phrases "Looker experience", "validated LookML" and equivalents are
  forbidden on every surface;
- the Looker gap is stated explicitly in the case study and application
  material, with the dated upgrade path (before 2026-08-16) noted;
- Looker Studio, documentation screenshots or training-lab work cannot
  upgrade this branch;
- no surface implies continuous production operation, real customer use or
  Monzo affiliation.

All claims trace to [evidence/registry.yml](../../evidence/registry.yml);
`tests/evidence/` enforces the branch rules mechanically.

## Consequences

- README, case study, dataset card, CV and interview materials are written
  against this branch's permitted wording only.
- If genuine Looker validation happens within the documented window, the
  branch upgrades to `full` by dated addendum here and in the registry —
  never by silently editing existing claims.
