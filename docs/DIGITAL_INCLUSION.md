# Digital Inclusion & Onboarding Funnel

Growth that quietly excludes people is not good growth. This module adds a synthetic
onboarding/KYC funnel and the analysis to answer: **who drops out of onboarding,
which segments are underserved, and who should be offered an assisted journey**
rather than left to fail the standard flow.

## Where it lives

| Concern | Location |
| --- | --- |
| Synthetic funnel generator | [`data_generator/onboarding.py`](../data_generator/onboarding.py) → `onboarding_events` table |
| dbt mart | [`dbt_neobank/models/marts/product/fct_onboarding_funnel.sql`](../dbt_neobank/models/marts/product/fct_onboarding_funnel.sql) |
| Funnel / exclusion analysis | [`src/inclusion/onboarding_funnel.py`](../src/inclusion/onboarding_funnel.py) |
| Dashboard view | "Digital inclusion" tab |
| Tests | [`tests/test_digital_inclusion.py`](../tests/test_digital_inclusion.py) |

## The funnel

A sequential, monotonic funnel where drop-off is correlated with digital confidence,
new-to-UK status, and accessibility need:

```text
signup_started -> identity_check_started -> identity_check_passed -> card_activated
```

`fct_onboarding_funnel` is one row per user with the step flags, `completed_onboarding`,
the `abandoned_step` (null when completed), `needs_assisted_onboarding`, and the
wellbeing/inclusion segment bands for slicing.

## Analysis

- **`funnel_conversion`** — per-step reach, overall rate, and step-over-step
  conversion.
- **`abandonment_by_segment`** — completion, abandonment, and assisted-need rates per
  segment level (e.g. `digital_confidence_band`, `income_band`), worst first.
- **`assisted_onboarding_segments`** — segment levels whose abandonment exceeds an
  acceptable threshold; the candidates for an assisted-onboarding variant.

## Example

```python
from src.inclusion import abandonment_by_segment, assisted_onboarding_segments

abandonment_by_segment(funnel, "digital_confidence_band")
# level   customers  completion_rate  abandonment_rate  assisted_need_rate
# low     ...        ...              0.41              ...
# medium  ...        ...              0.24              ...
# high    ...        ...              0.17              ...

assisted_onboarding_segments(funnel, "digital_confidence_band",
                             max_acceptable_abandonment=0.25)
# -> [AssistedOnboardingFlag(level="low", abandonment_rate=0.41, ...)]
```

## Boundary

Inclusion proxies are synthetic and exist only to **target supportive
interventions** (assisted onboarding, clearer communication, accessibility support).
They must never be used to deny, delay, or restrict access.
