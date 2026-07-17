"""Referral invitation and qualification (family: referral_reward)."""

from datetime import datetime, timedelta

from src.event_simulator.state import ReferralLifecycle


def invite(config, emitter, ids, rng, journey) -> None:
    lifecycle = ReferralLifecycle(journey.referral_id)
    lifecycle.advance("invited")
    emitter.truth.referral_end_states[journey.referral_id] = lifecycle.state
    emitter.emit(
        "referral-invited",
        1,
        business_key=f"invite:{journey.referral_id}",
        occurred=journey.applied_at - timedelta(days=1),
        payload={
            "referral_id": journey.referral_id,
            "referrer_customer_id": journey.referrer_customer_id,
            "invite_channel": "in_app_link" if rng.random() < 0.7 else "share_code",
        },
        trace=f"referral:{journey.referral_id}",
    )


def qualify(config, emitter, ids, rng, journey, funded_at: datetime) -> bool:
    """Qualification follows first funding; emits v1 or v2 per the configured
    share. Returns True when the referral qualified."""
    lifecycle = ReferralLifecycle(journey.referral_id)
    lifecycle.state = "invited"
    lifecycle.advance("qualified")
    emitter.truth.referral_end_states[journey.referral_id] = lifecycle.state
    emitter.truth.entitled_minor += config.reward_amount_minor

    use_v2 = rng.random() < config.scenario_mix.v2_share
    payload = {
        "referral_id": journey.referral_id,
        "referrer_customer_id": journey.referrer_customer_id,
        "referred_customer_id": journey.customer_id,
        "qualified_reason": "first_funding_completed",
    }
    if use_v2:
        payload["qualification_rule"] = "rule_v2_first_funding_within_30d"
        payload["qualifying_account_id"] = journey.account_id
    emitter.emit(
        "referral-qualified",
        2 if use_v2 else 1,
        business_key=f"qualify:{journey.referral_id}",
        occurred=funded_at + timedelta(minutes=5),
        payload=payload,
        trace=f"referral:{journey.referral_id}",
    )
    return True
