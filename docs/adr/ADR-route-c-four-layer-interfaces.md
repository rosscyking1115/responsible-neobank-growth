# ADR: Route C four-layer warehouse and governed interfaces

## Status

Accepted — 2026-07-17 (Plan 1, Task 2).

## Context

The current dbt project uses staging/intermediate/mart layers with no formal
interface concept: any mart can become a de-facto contract, and nothing states which
relation owns a business meaning. Route C needs explicit ownership so that Growth,
Finance and platform consumers (including future Looker Explores) read governed,
versioned interfaces instead of accidental structure.

## Decision

The target model directories and prefixes are locked:

```text
dbt_neobank/models/
  landing/       # lnd_*
  normalised/    # nrm_*
  logical/       # lgl_*
  presentation/  # prs_*
```

| Layer | Owns | Must not own |
|---|---|---|
| Landing (`lnd_`) | payload flattening, ingestion metadata, deduplication, quarantine | reusable business metrics |
| Normalised (`nrm_`) | immutable canonical events, entities, SCD2/current state | consumer-specific labels or dashboards |
| Logical (`lgl_`) | cross-entity business logic and governed reusable interfaces | Looker formatting or one-off presentation logic |
| Presentation (`prs_`) | consumer-shaped outputs for Looker, Finance, reporting and ML | alternative definitions of governed business truth |

Only normalised and logical models may become cross-domain governed interfaces.
Presentation models are replaceable consumers.

**Compatibility rule:** existing models do not move or disappear in one commit.
Plan 2 must use one of: a compatibility view with the old relation name; a versioned
model contract; or a deliberately deprecated output with a migration record and
consumer test.

**Interface governance:** every governed interface carries a manifest
(`contracts/interfaces/`) declaring owner, purpose, grain, unique key, freshness SLO,
classification, allowed consumers, compatibility policy, tests and exposures. The
four Route C interfaces and their ownership:

- `growth_acquisition` — Growth owns meaning; platform owns reliability.
- `referral_economics` — Growth owns qualification/effectiveness; Finance owns booked reward cost.
- `reward_reconciliation` — Finance owns reconciliation rules; platform owns event/model correctness.
- `warehouse_health` — platform owns freshness, quality, runtime and cost definitions.

## Alternatives considered

- **Keep staging/intermediate/mart:** rejected for governed work — it cannot express
  the landing/canonical split that duplicate suppression and quarantine require.
- **One-commit rename of existing models:** rejected — destroys validated consumers;
  forbidden by the compatibility rule.

## Consequences

- Layer responsibilities become mechanically inspectable (standards-as-code checks
  naming, layer and manifest completeness).
- Every headline metric receives exactly one authoritative persisted grain and one
  semantic owner (see ADR-route-c-dbt-looker-boundary).
- Migration cost is explicit: every current model gets a target action in
  `docs/migration/route-c-model-inventory.csv` before Gate 0 is decided.
