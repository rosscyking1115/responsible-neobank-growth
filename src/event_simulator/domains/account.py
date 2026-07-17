"""Account activation and first funding (family: activation_funding)."""

from datetime import datetime, timedelta

FUNDING_METHODS = ["bank_transfer", "debit_card", "salary"]
FUNDING_WEIGHTS = [0.6, 0.3, 0.1]


def generate(config, emitter, ids, rng, journey) -> datetime | None:
    """Emit activation (always, post-approval) and first funding (~85%).

    Returns the funding time, or None if the customer never funds.
    """
    activated_at = journey.applied_at + timedelta(hours=1, minutes=rng.randrange(0, 180))
    journey.activated_at = activated_at
    emitter.emit(
        "account-activated",
        1,
        business_key=f"activate:{journey.account_id}",
        occurred=activated_at,
        payload={
            "account_id": journey.account_id,
            "customer_id": journey.customer_id,
            "application_id": journey.application_id,
        },
        trace=journey.trace,
    )

    if rng.random() >= 0.85:
        return None
    funded_at = activated_at + timedelta(hours=rng.randrange(1, 72))
    emitter.emit(
        "account-funded",
        1,
        business_key=f"fund:{journey.account_id}:first",
        occurred=funded_at,
        payload={
            "account_id": journey.account_id,
            "customer_id": journey.customer_id,
            "amount_minor": rng.randrange(1_000, 50_000),
            "currency": "GBP",
            "funding_method": rng.choices(FUNDING_METHODS, weights=FUNDING_WEIGHTS, k=1)[0],
            "is_first_funding": True,
        },
        trace=journey.trace,
    )
    return funded_at
