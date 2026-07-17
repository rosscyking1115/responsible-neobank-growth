# ADR: Route C dbt/LookML responsibility boundary

## Status

Accepted — 2026-07-17 (Plan 1, Task 2).

## Context

When a BI layer is added on top of a warehouse, business logic tends to get
reimplemented twice — once in dbt, once in the semantic model — and the two drift.
Route C plans a genuine Looker/LookML layer (Plan 3), so the responsibility boundary
must be locked before any LookML exists.

## Decision

**Metric ownership rule:** every headline metric receives exactly **one authoritative**
persisted grain and one semantic owner, recorded in `docs/metrics/metric-ownership.yml`.

**dbt owns:**

- event version adaptation, deduplication and state reconstruction;
- referral eligibility and reward entitlement;
- experiment/causal adjustments;
- ledger entries and reconciliation status;
- governed persisted grains;
- warehouse job/freshness/test evidence.

**LookML owns:**

- user-facing field names and descriptions;
- reusable additive/semi-additive measures over approved grains;
- explicit Explore joins and relationships;
- curated field sets, drill paths and access grants;
- cache policy and decision-focused dashboard composition.

LookML **may not reimplement** eligibility, lifecycle state reconstruction, causal
adjustment, reconciliation logic or incremental processing. Looker connects only to
approved presentation/logical interfaces — never to raw payloads or version-specific
landing models.

## Alternatives considered

- **Define metrics in LookML only:** rejected — non-Looker consumers (API, ML,
  Streamlit) would lose access to governed definitions.
- **dbt Semantic Layer:** not adopted; the project uses governed dbt marts/interfaces
  and must not claim Semantic Layer usage unless one is actually implemented.

## Consequences

- Plan 3's LookML work is additive semantics over stable grains, so a Looker trial
  can be spent validating rather than re-deriving logic.
- A duplicated authoritative metric owner is a test failure
  (`tests/contracts/test_interface_contracts.py`).
- If Looker access never materialises, the governed interfaces still serve every
  other consumer unchanged — the boundary loses nothing on the `partial go` branch.
