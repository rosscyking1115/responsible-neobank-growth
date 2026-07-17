"""Late-arrival scenarios: inside-lookback late deliveries (repaired by an
ordinary incremental run) and beyond-lookback deliveries (requiring bounded
backfill). Delivery defect only — occurrence time never changes."""

from datetime import datetime, timedelta

_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _eligible(deliveries, config):
    latest_occurrence = config.clock_end - timedelta(days=config.lookback_days + 2)
    cutoff = latest_occurrence.strftime(_FMT)
    return sorted(
        (e for e in deliveries if e["occurred_at"] <= cutoff),
        key=lambda e: e["event_id"],
    )


def inject(deliveries, config, rng) -> None:
    pool = _eligible(deliveries, config)
    threshold_h = config.late_threshold_hours
    lookback_h = config.lookback_days * 24

    within_count = max(1, int(config.scenario_mix.late_arrival_rate * len(pool)))
    beyond_count = config.scenario_mix.beyond_lookback_count
    chosen = rng.sample(pool, min(within_count + beyond_count, len(pool)))
    within, beyond = chosen[:within_count], chosen[within_count:]

    for event in within:
        occurred = datetime.strptime(event["occurred_at"], _FMT)
        delay_hours = threshold_h + rng.uniform(1, lookback_h - threshold_h - 1)
        event["ingested_at"] = (occurred + timedelta(hours=delay_hours)).strftime(_FMT)
        event["scenario_id"] = "late-arrival"

    for event in beyond:
        occurred = datetime.strptime(event["occurred_at"], _FMT)
        delay_hours = lookback_h + 1 + rng.uniform(0, 24)
        event["ingested_at"] = (occurred + timedelta(hours=delay_hours)).strftime(_FMT)
        event["scenario_id"] = "beyond-lookback-arrival"
