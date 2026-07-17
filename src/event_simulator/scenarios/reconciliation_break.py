"""Reconciliation-break scenario: a qualified referral's reward posting is
intentionally omitted, creating exactly one missing_posting exception each."""


def inject(deliveries, truth, config, rng, exclude_rewards: set[str]) -> int:
    count = config.scenario_mix.reconciliation_break_count
    if count == 0:
        return 0
    booked_by_referral = {
        e["payload"]["referral_id"]: e
        for e in deliveries
        if e["event_name"] == "reward-booked"
        and e["payload"]["reward_id"] not in exclude_rewards
    }
    settled_by_reward = {
        e["payload"]["reward_id"]: e for e in deliveries if e["event_name"] == "reward-settled"
    }
    pool = sorted(booked_by_referral)
    chosen = rng.sample(pool, min(count, len(pool)))

    for referral_id in sorted(chosen):
        booked = booked_by_referral[referral_id]
        amount = booked["payload"]["amount_minor"]
        reward_id = booked["payload"]["reward_id"]
        deliveries.remove(booked)
        truth.booked_minor -= amount
        settled = settled_by_reward.get(reward_id)
        if settled is not None:
            deliveries.remove(settled)
            truth.settled_minor -= settled["payload"]["amount_minor"]
        truth.referral_end_states[referral_id] = "qualified"
    return len(chosen)
