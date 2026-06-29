# Responsible Release-Gate Framework

The release-gate engine turns analysis into an **explainable decision**. Instead of
only reporting metrics, it answers: *should this onboarding, pricing, referral, or
product change ship, ramp slowly, stay an experiment, go to human review, or be
blocked?*

The guiding principle: **customer-outcome concerns dominate commercial evidence.**
A strong uplift never overrides a block-level harm signal.

## Where it lives

| Concern | Location |
| --- | --- |
| Decision engine | [`src/release_decisions/decision_engine.py`](../src/release_decisions/decision_engine.py) |
| Configurable thresholds | [`src/release_decisions/thresholds.py`](../src/release_decisions/thresholds.py) |
| Markdown memo | [`src/release_decisions/report.py`](../src/release_decisions/report.py) |
| Tests | [`tests/test_release_decisions.py`](../tests/test_release_decisions.py) |

## Decisions

| Decision | Meaning |
| --- | --- |
| `ship` | Ship-grade evidence and no material customer-outcome concern. |
| `limited_rollout` | Positive evidence but some uncertainty or a warn-level guardrail. |
| `experiment_only` | Promising, but evidence is not strong enough for rollout. |
| `needs_human_review` | Sensitive-group impact, ambiguous result, or operational risk. |
| `block` | Significant harm signal, fairness gap, or data-quality failure. |

## How a decision is reached

The engine evaluates two things independently and then combines them:

1. **Evidence tier** (`ship` / `rollout` / `insufficient`) from business uplift,
   evidence strength, confirmed incrementality, and experiment validity.
2. **Guardrail checks** — each returns `pass` / `warn` / `review` / `block` across
   complaint risk, support burden, fairness gap, vulnerable-customer impact,
   fair-value score, model calibration, model drift, data quality, and human-review
   load.

Resolution order (highest precedence first):

```text
any guardrail = block          -> block
any guardrail = review         -> needs_human_review
evidence      = insufficient   -> experiment_only
evidence = ship AND no warns   -> ship
otherwise                      -> limited_rollout
```

## Example

```python
from src.release_decisions import ReleaseSignals, decide
from src.release_decisions.report import render_decision_markdown

signals = ReleaseSignals(
    feature_name="personalised_onboarding_pot_prompt",
    business_uplift=0.031,          # +3.1pp activation
    evidence_strength=0.78,
    support_burden_delta=0.015,     # support load up for some users
    fairness_gap=0.04,
    vulnerable_customer_impact=0.0,
    fair_value_score=0.8,
)
decision = decide(signals)
print(decision.decision)            # -> "limited_rollout"
print(render_decision_markdown(decision))
```

Output (abridged):

```text
Release decision: LIMITED ROLLOUT
- Evidence rollout-grade (uplift=+0.031, strength=0.78).
- Proceed with a limited rollout. Caveats:
- support-burden delta: 0.015 (warn>=0.01, block>=0.03)
```

Thresholds are fully configurable via `ReleaseThresholds` for stricter or more
permissive regimes.
