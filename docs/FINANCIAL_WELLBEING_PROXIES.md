# Financial Wellbeing Proxies

The wellbeing layer adds synthetic, per-customer **financial-wellbeing proxies** so
product decisions can be evaluated against customer-outcome and fairness signals,
not only commercial uplift. It is the data foundation for the planned Customer
Outcomes & Fairness view, digital-inclusion analysis, and responsible release gates.

> **Important boundary.** These fields are a *simulation*. They are **not** a real
> vulnerability classifier and must never be used for credit, pricing-penalty,
> account-closure, fraud-blocking, punitive, or service-denial decisions. The
> boundary is enforced in code — see [Permitted and prohibited uses](#permitted-and-prohibited-uses).

## Where it lives

| Concern | Location |
| --- | --- |
| Synthetic generator | [`data_generator/wellbeing.py`](../data_generator/wellbeing.py) → `wellbeing_proxies` table |
| Use-boundary guardrails | [`src/wellbeing/guardrails.py`](../src/wellbeing/guardrails.py) |
| Segment outcome / fairness-gap metrics | [`src/wellbeing/metrics.py`](../src/wellbeing/metrics.py) |
| Tests | [`tests/test_wellbeing.py`](../tests/test_wellbeing.py) |

The table is emitted by the standard data generator and flows through the cloud
export manifest like every other table.

## Data dictionary — `wellbeing_proxies`

| Field | Type | Meaning |
| --- | --- | --- |
| `customer_id` | str | Joins to `users.user_id`. |
| `income_band` | str | Coarse band (`low` / `medium` / `high`) derived from income segment. |
| `income_volatility_score` | float [0,1] | Higher = less predictable income. |
| `salary_regularity_score` | float [0,1] | Higher = more regular salary credits. |
| `cash_buffer_proxy` | float [0,1] | Higher = larger savings/cash cushion. |
| `bill_pressure_score` | float [0,1] | Higher = more income committed to bills. |
| `overdraft_risk_proxy` | float [0,1] | Rises with bill pressure and volatility, falls with cash buffer. |
| `missed_payment_proxy` | bool | Synthetic missed-payment signal correlated with overdraft risk. |
| `support_contact_frequency` | int | Proxy contact count; higher for lower digital confidence and flagged customers. |
| `complaint_history_flag` | bool | Synthetic prior-complaint signal. |
| `digital_confidence_score` | float [0,1] | Lower for older customers and the most strained segments. |
| `accessibility_need_proxy` | bool | Synthetic accessibility-need signal (higher for 65+). |
| `new_to_uk_proxy` | bool | Synthetic new-to-UK signal. |
| `student_proxy` | bool | Student indicator. |
| `vulnerable_customer_proxy` | bool | Superset of `users.vulnerable_customer_flag` plus a strong-strain signal. |

All scores are deterministic for a given generator seed and correlated with income
segment, age, and the existing vulnerable flag, with independent noise so segments
are not perfectly separable.

## Permitted and prohibited uses

These lists are executable via `assert_permitted_use` / `assert_supportive_decision`
in [`src/wellbeing/guardrails.py`](../src/wellbeing/guardrails.py); unknown uses are
rejected by default.

**Permitted:** supportive onboarding, experiment monitoring, customer-outcome
analysis, pricing-scenario governance, fairness-gap detection, support-burden
monitoring, responsible release planning.

**Prohibited:** credit eligibility, account closure, punitive treatment, unfair
pricing, real vulnerability labelling, financial advice, automated fraud blocking,
denial of services.

Decisions triggered off wellbeing signals are restricted to a supportive set
(assisted onboarding, clearer communication, education prompts, soft friction,
cooling-off, prioritised support, human review, monitor, no action).

## Example use

```python
from src.wellbeing.guardrails import assert_permitted_use
from src.wellbeing.metrics import outcome_gap

assert_permitted_use("fairness_gap_detection")
gap = outcome_gap(frame, segment="digital_confidence_band", outcome="failed_onboarding")
# gap.gap is the failed-onboarding disparity between the best- and worst-served bands.
```
