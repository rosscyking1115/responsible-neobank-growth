"""Reversal scenario: a booked reward is reversed instead of settling.

Business-state change: the settlement delivery is replaced with a
reward-reversed event, the referral terminates at ``reversed`` and the ledger
truth moves the amount from settled to reversed.
"""

from datetime import datetime, timedelta


def inject(deliveries, truth, config, rng, ids) -> set[str]:
    settled_by_reward = {
        e["payload"]["reward_id"]: e for e in deliveries if e["event_name"] == "reward-settled"
    }
    booked_by_reward = {
        e["payload"]["reward_id"]: e for e in deliveries if e["event_name"] == "reward-booked"
    }
    pool = sorted(set(settled_by_reward) & set(booked_by_reward))
    count = max(1, int(config.scenario_mix.reversal_rate * len(pool))) if pool else 0
    chosen = rng.sample(pool, min(count, len(pool)))

    for index, reward_id in enumerate(sorted(chosen)):
        settled = settled_by_reward[reward_id]
        booked = booked_by_reward[reward_id]
        referral_id = booked["payload"]["referral_id"]
        amount = settled["payload"]["amount_minor"]
        deliveries.remove(settled)

        occurred = datetime.strptime(settled["occurred_at"], "%Y-%m-%dT%H:%M:%SZ")
        emitted = occurred + timedelta(seconds=1)
        ingested = emitted + timedelta(seconds=2)
        deliveries.append(
            {
                "event_id": ids.event_id("reward-reversed", 3_000_000 + index),
                "idempotency_key": ids.idempotency_key(f"reverse:{reward_id}"),
                "event_name": "reward-reversed",
                "source_service": "rewards-service",
                "occurred_at": occurred.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "emitted_at": emitted.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ingested_at": ingested.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "schema_version": 1,
                "producer_id": "rewards-service-01",
                "trace_id": settled["trace_id"],
                "payload": {
                    "reward_id": reward_id,
                    "reversal_id": ids.reversal_id(3_000_000 + index),
                    "amount_minor": amount,
                    "currency": "GBP",
                    "reversal_reason": "qualification_withdrawn",
                },
                "generator_version": config.generator_version,
                "scenario_id": "reversal",
            }
        )
        truth.settled_minor -= amount
        truth.reversed_minor += amount
        truth.referral_end_states[referral_id] = "reversed"
    return set(chosen)
