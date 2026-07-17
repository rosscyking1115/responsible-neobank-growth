"""Malformed-payload scenario: new deliveries claiming schema v2 without the
required qualification_rule. They must land in quarantine with evidence and
never mutate canonical state (fresh idempotency keys, so nothing is masked)."""

from datetime import datetime, timedelta

_FMT = "%Y-%m-%dT%H:%M:%SZ"


def inject(deliveries, config, rng, ids) -> int:
    qualified = sorted(
        (e for e in deliveries if e["event_name"] == "referral-qualified"),
        key=lambda e: e["event_id"],
    )
    count = max(1, int(config.scenario_mix.malformed_rate * len(deliveries)))
    chosen = rng.sample(qualified, min(count, len(qualified)))

    for index, original in enumerate(sorted(chosen, key=lambda e: e["event_id"])):
        payload = {
            key: value
            for key, value in original["payload"].items()
            if key in {
                "referral_id",
                "referrer_customer_id",
                "referred_customer_id",
                "qualified_reason",
            }
        }  # v2 requires qualification_rule; omitting it makes the payload invalid
        ingested = datetime.strptime(original["ingested_at"], _FMT) + timedelta(
            minutes=rng.randrange(1, 45)
        )
        deliveries.append(
            {
                **original,
                "payload": payload,
                "schema_version": 2,
                "event_id": ids.event_id("referral-qualified", 2_000_000 + index),
                "idempotency_key": ids.idempotency_key(f"malformed:{index}"),
                "ingested_at": min(
                    ingested.strftime(_FMT), config.clock_end.strftime(_FMT)
                ),
                "scenario_id": "malformed-quarantine",
            }
        )
    return len(chosen)
