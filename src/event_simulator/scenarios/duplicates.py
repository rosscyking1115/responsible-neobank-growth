"""Duplicate-delivery scenario: exact redeliveries sharing the idempotency key
with a distinct delivery identity and later arrival. Canonical business state
must count them once (delivery defect only)."""

from datetime import datetime, timedelta


def inject(deliveries, config, rng, ids) -> int:
    pool = sorted(
        (e for e in deliveries if e["event_name"] != "reward-reversed"),
        key=lambda e: e["event_id"],
    )
    count = max(1, int(config.scenario_mix.duplicate_delivery_rate * len(pool)))
    chosen = rng.sample(pool, min(count, len(pool)))

    end = config.clock_end.strftime("%Y-%m-%dT%H:%M:%SZ")
    for index, original in enumerate(sorted(chosen, key=lambda e: e["event_id"])):
        ingested = datetime.strptime(original["ingested_at"], "%Y-%m-%dT%H:%M:%SZ") + timedelta(
            minutes=rng.randrange(1, 30)
        )
        duplicate = {
            **original,
            "payload": dict(original["payload"]),
            "event_id": ids.event_id(original["event_name"], 1_000_000 + index),
            "ingested_at": min(ingested.strftime("%Y-%m-%dT%H:%M:%SZ"), end),
            "scenario_id": "duplicate-delivery",
        }
        deliveries.append(duplicate)
    return len(chosen)
