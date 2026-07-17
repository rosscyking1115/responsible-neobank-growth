"""Customer-outcome guardrail signals (family: customer_outcome).

Bounded guardrail only: synthetic proxies for complaints/support/hardship, per
the use boundaries in docs/FINANCIAL_WELLBEING_PROXIES.md.
"""

from datetime import timedelta

OUTCOME_TYPES = ["support_contact", "complaint", "hardship_indicator"]
OUTCOME_WEIGHTS = [0.70, 0.20, 0.10]
SEVERITIES = ["low", "medium", "high"]
SEVERITY_WEIGHTS = [0.6, 0.3, 0.1]


def generate(config, emitter, ids, rng, journey) -> None:
    if rng.random() >= 0.08 or journey.activated_at is None:
        return
    emitter.emit(
        "customer-outcome-recorded",
        1,
        business_key=f"outcome:{journey.customer_id}:1",
        occurred=journey.activated_at + timedelta(days=rng.randrange(1, 14)),
        payload={
            "customer_id": journey.customer_id,
            "outcome_type": rng.choices(OUTCOME_TYPES, weights=OUTCOME_WEIGHTS, k=1)[0],
            "severity": rng.choices(SEVERITIES, weights=SEVERITY_WEIGHTS, k=1)[0],
        },
        trace=journey.trace,
    )
