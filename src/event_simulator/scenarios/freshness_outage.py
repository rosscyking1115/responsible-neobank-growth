"""Freshness-outage scenario: a 96-hour ingestion gap in the middle of the
window. Arrivals inside the outage are delayed until it ends, preserving their
relative order; occurrence times never change."""

from datetime import timedelta

_FMT = "%Y-%m-%dT%H:%M:%SZ"
OUTAGE_HOURS = 96
THRESHOLD_HOURS = 72


def inject(deliveries, config, rng) -> dict | None:
    if not config.scenario_mix.freshness_outage:
        return None
    span = config.clock_end - config.clock_start
    outage_start = config.clock_start + span * 0.5
    outage_end = outage_start + timedelta(hours=OUTAGE_HOURS)
    start_s, end_s = outage_start.strftime(_FMT), outage_end.strftime(_FMT)

    delayed = sorted(
        (e for e in deliveries if start_s <= e["ingested_at"] < end_s),
        key=lambda e: (e["ingested_at"], e["event_id"]),
    )
    for index, event in enumerate(delayed):
        event["ingested_at"] = (outage_end + timedelta(seconds=index)).strftime(_FMT)
        event["scenario_id"] = "freshness-outage"

    return {
        "outage_start": start_s,
        "outage_end": end_s,
        "threshold_hours": THRESHOLD_HOURS,
        "delayed_deliveries": len(delayed),
    }
