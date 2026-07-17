"""Reward booking and settlement (family: referral_reward).

Valid generation books every qualified referral and settles it when the
settlement date fits the window; reversals and reconciliation breaks are fault
scenarios (Task 3), not part of the valid lifecycle stream.
"""

from datetime import datetime, timedelta

from src.event_simulator.state import ReferralLifecycle


def generate(config, emitter, ids, rng, journey, funded_at: datetime) -> None:
    lifecycle = ReferralLifecycle(journey.referral_id)
    lifecycle.state = "qualified"

    reward_id = ids.reward_id(journey.sequence)
    booked_at = funded_at + timedelta(hours=1)
    lifecycle.advance("booked")
    emitter.truth.booked_minor += config.reward_amount_minor
    emitter.emit(
        "reward-booked",
        1,
        business_key=f"book:{reward_id}",
        occurred=booked_at,
        payload={
            "reward_id": reward_id,
            "referral_id": journey.referral_id,
            "beneficiary_customer_id": journey.referrer_customer_id,
            "amount_minor": config.reward_amount_minor,
            "currency": "GBP",
        },
        trace=f"referral:{journey.referral_id}",
    )
    emitter.truth.referral_end_states[journey.referral_id] = lifecycle.state

    settled_at = booked_at + timedelta(days=rng.randrange(5, 10))
    if settled_at >= config.clock_end:
        return
    lifecycle.advance("settled")
    emitter.truth.settled_minor += config.reward_amount_minor
    emitter.emit(
        "reward-settled",
        1,
        business_key=f"settle:{reward_id}",
        occurred=settled_at,
        payload={
            "reward_id": reward_id,
            "settlement_id": ids.settlement_id(journey.sequence),
            "amount_minor": config.reward_amount_minor,
            "currency": "GBP",
        },
        trace=f"referral:{journey.referral_id}",
    )
    emitter.truth.referral_end_states[journey.referral_id] = lifecycle.state
