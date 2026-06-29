# Customer Protection / Scam-Intervention Simulation

A scoped, **responsible-intervention** simulation. It maps risk signals on a transfer
to a *supportive* response — education, soft friction, a cooling-off period, or a
human-review recommendation. It is deliberately **not** a fraud engine: it never
blocks a payment or makes a punitive decision.

> A full fraud platform needs real transaction graphs, device fingerprints, confirmed
> fraud labels, and fraud-ops feedback. This module models risk-triggered *support and
> education* on synthetic data instead.

## Where it lives

| Concern | Location |
| --- | --- |
| Synthetic event generator | [`data_generator/protection.py`](../data_generator/protection.py) → `protection_events` |
| dbt feed | `stg_protection_events` → [`fct_protection_events`](../dbt_neobank/models/marts/product/fct_protection_events.sql) |
| Rules engine | [`src/protection/scam_intervention_sim.py`](../src/protection/scam_intervention_sim.py) |
| Configurable weights/thresholds | [`src/protection/friction_rules.py`](../src/protection/friction_rules.py) |
| Dashboard view | "Customer protection" tab |
| Tests | [`tests/test_customer_protection.py`](../tests/test_customer_protection.py) |

The intervention **decision** lives in Python (one tested place), not in SQL; the dbt
mart is just the cleaned event feed the rules consume.

## Risk signals

`new_payee`, `first_large_transfer`, large `amount_gbp`, `unusual_time`,
`recent_device_change`, `ignored_warning`, `support_contact_about_scam`,
`investment_context`, and `vulnerable_customer` raise a 0..1 risk score; an explicit
`confirmed_transfer` or a heeded scam warning slightly lower it.

## Supportive responses

| Action | When |
| --- | --- |
| `human_review_recommendation` | Customer contacted support about a scam, or high risk **and** vulnerable. |
| `cooling_off_period` | High risk score. |
| `soft_friction` | Medium risk score. |
| `education_prompt` | Low risk, or any investment-scam context. |
| `no_action` | No elevated risk. |

Every possible action is in `SUPPORTIVE_ACTIONS` — there is no path to a block or
denial. A test asserts no combination of signals can produce a punitive outcome.

## Example

```python
from src.protection import ProtectionEvent, decide_intervention

decide_intervention(
    ProtectionEvent(
        event_id="prot_1",
        new_payee=True,
        first_large_transfer=True,
        amount_gbp=5000.0,
        recent_device_change=True,
        ignored_warning=True,
        viewed_scam_warning=True,
    )
).action  # -> "cooling_off_period"

decide_intervention(
    ProtectionEvent(event_id="prot_2", support_contact_about_scam=True)
).action  # -> "human_review_recommendation"
```
