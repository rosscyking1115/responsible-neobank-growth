# Maintenance policy

> In force from v1.0.0 (2026-07-17). The Route C programme is released and
> feature-frozen.

## Scope freeze

Feature work on this project is frozen. It is a released reference project, not
an actively growing product, and adding banking features or dashboards to signal
activity is explicitly out of scope. Work proceeds only when one of these holds:

- a reproducibility or security defect is reported;
- a real user requests a bounded scenario or adapter that fits the benchmark;
- a Monzo interview or take-home exposes a genuine modelling gap;
- a dependency or platform change breaks the verified path;
- a lawful real-data partnership provides a clear new research question.

## How corrections are made

Benchmark results are never altered in place. A correction gets a dated record
and, if it changes a public number, a new version — the evidence registry and
claim audit stay the source of truth. Historical evidence is marked, not
rewritten.

## Looker upgrade path

The LookML is authored, not validated. If a genuine no-cost Looker trial is
provisioned before the 2026-08-16 cleanup deadline, run the validators
(`docs/looker/trial-runbook.md`), capture the evidence
(`docs/looker/evidence-checklist.md`), and upgrade the record by dated addendum
to `docs/adr/ADR-route-c-plan3-decision.md` and the evidence registry. Never
promote the Looker claim by editing existing wording.

## Cloud cleanup

The five labelled `neobank_p3_*` BigQuery datasets are retained until
**2026-08-16** (storage-only, free tier) and deleted at or before that date per
`cloud/gcp/plan3/cleanup-runbook.md`, unless a Looker validation upgrade uses
them first.

## Release verification

Any patch release repeats the release-candidate check
(`tools/release/release_check.py`) and the clean-clone reproduction before
tagging.
