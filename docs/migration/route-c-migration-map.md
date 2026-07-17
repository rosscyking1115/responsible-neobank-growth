# Route C Migration Map

> **Status:** Accepted 2026-07-17 (Plan 1, Task 5). Summarises how the current
> repository migrates to the event-to-interface architecture without destroying
> validated capability. Row-level decisions:
> [route-c-model-inventory.csv](route-c-model-inventory.csv); consumer surfaces:
> [route-c-consumer-map.md](route-c-consumer-map.md).

## Migration boundary

The event boundary covers exactly the six locked source families (campaign spend;
application/KYC/account; activation/funding; referral/reward; experiment;
customer outcome). Everything else — sessions, feature events, pricing, wellbeing
proxies, protection simulation, ground-truth references — is **retained batch
context**: preserved as-is, feeding preserved consumers, marked
`synthetic_source_family: none` in the inventory.

Within the boundary, migration is by **compatibility, not rewrite**
(ADR-route-c-four-layer-interfaces): each superseded relation keeps its name as a
compatibility view over the new governed model until its consumers are verified
against the new source. Nothing is deleted in Plan 2.

## Decision counts (from the inventory)

- 16 raw tables: 4 migrate into event landing models, 12 preserve.
- 16 staging models: 4 migrate to normalised canonical models, 12 preserve.
- 3 intermediate models: 2 migrate, 1 preserve.
- 15 marts: 3 migrate (activation, customer outcomes, onboarding funnel),
  4 become downstream consumers of governed interfaces, 8 preserve.
- 0 rows deprecated or removed in Plan 1; `deprecate_with_evidence` and
  `remove_unsupported_claim` remain available for Plan 2 findings.

## Preservation threshold (Gate G0.4)

The threshold is preservation of **validated capability**, not percentage of lines
retained. It passes because:

1. **Every current asset has a decision** — no inventory row is unclassified
   (enforced by `tests/migration/test_route_c_inventory.py`).
2. **Claims tie to evidence** — every public claim is inventoried in
   [route-c-claim-inventory.csv](route-c-claim-inventory.csv) as verified,
   historical-labelled, or flagged (one known documentation contradiction is
   recorded for Plan 4 resolution, not silently rewritten).
3. **Core paths have a compatibility route** — activation (`fct_activation`),
   experiments (`fct_experiment_user_metrics`), referrals (`stg_referrals` and geo
   referral marts), unit economics (reward subledger, new) and customer outcomes
   (`fct_customer_outcomes`) all map to governed interfaces with
   `compatibility_view` or `downstream_consumer` routes.
4. **No consumer reads version-specific landing payloads** — Streamlit, API, ML
   and Looker consumers are mapped to normalised/logical/presentation relations
   only.
5. **Anchor consumer** — the Experiments tab plus release-gate engine
   (`fct_experiment_user_metrics`) is the existing downstream consumer that must be
   supplied *entirely* through the proposed `growth_acquisition` governed interface
   in Plan 2; its contract test is specified in Plan 2 Task 10.

## What the migration deliberately does not do

- No general banking simulator: families outside the locked six stay batch.
- No rewrite of Streamlit/API/ML internals — only their data boundary may change
  ("demotion rather than rewrite", Plan 2 Section 12.3).
- No count inflation: migrated models replace, and compatibility views are not
  double-counted as new capability (Plan 3 Section 8.2 rule).
