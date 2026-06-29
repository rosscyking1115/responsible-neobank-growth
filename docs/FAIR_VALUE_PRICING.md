# Fair-Value Pricing Governance

The commercial pricing mart recommends an action for each offer (`scale` / `test` /
`hold_*` / `human_review`) based on margin and conversion. Fair-value governance adds
a **fairness lens** on top: an offer that looks attractive commercially can still be
held or escalated if its observed customer-outcome guardrails point to poor customer
value. This applies the release-gate thesis — customer fairness can override
commercial appeal — to pricing.

## Where it lives

| Concern | Location |
| --- | --- |
| Fair-value scoring + governance | [`src/pricing_governance/fair_value.py`](../src/pricing_governance/fair_value.py) |
| Dashboard aggregation helper | `offer_fair_value` in [`app/dashboard_data.py`](../app/dashboard_data.py) |
| Dashboard view | "Fair-Value Governance" section of the Pricing intelligence tab |
| Tests | [`tests/test_pricing_governance.py`](../tests/test_pricing_governance.py) |

## Fair-value score

A transparent 0..1 score (higher = fairer), penalised by three observed guardrails,
each normalised against a reference level and weighted:

```text
penalty = 0.40 * min(complaint_rate_14d / 0.025, 1)
        + 0.30 * min(support_contact_rate_14d / 0.20, 1)
        + 0.30 * min(human_review_rate / 0.25, 1)
fair_value_score = clip(1 - penalty, 0, 1)
```

All references and weights are configurable via `FairValueThresholds`.

## Governance action

| Action | When |
| --- | --- |
| `human_review` | A block-level guardrail is breached (complaint ≥ 2.5%, support ≥ 30%, or review ≥ 40%). |
| `hold_fair_value` | Fair-value score below the minimum (default 0.60); a "scale" offer here is **downgraded**. |
| `scale` | Strong fair value (≥ 0.75) **and** a positive commercial recommendation. |
| `monitor` | Acceptable fair value, but monitor before scaling. |

The `downgraded` flag marks offers the commercial mart wanted to `scale` but fairness
held back — the headline signal for a pricing reviewer.

## Example

```python
from src.pricing_governance import assess_offer

assessment = assess_offer(
    offer_id="teaser_bundle",
    complaint_rate_14d=0.02,
    support_contact_rate_14d=0.15,
    human_review_rate=0.20,
    mart_recommended_action="scale",
)
assessment.fair_value_score   # -> ~0.21
assessment.governance_action  # -> "hold_fair_value"
assessment.reason             # -> "Fair-value score below 0.60 (downgraded from scale)."
```
