"""Campaign spend events (family: campaign_spend)."""

from datetime import timedelta

CAMPAIGNS = [
    ("cmp_spring_boost", "paid_social"),
    ("cmp_always_on", "paid_search"),
]


def generate(config, emitter) -> None:
    """One spend record per campaign per week across the window."""
    week_start = config.clock_start
    week_index = 0
    while week_start + timedelta(days=7) <= config.clock_end:
        for campaign_id, channel in CAMPAIGNS:
            occurred = week_start + timedelta(hours=9)
            emitter.emit(
                "campaign-spend-recorded",
                1,
                business_key=f"spend:{campaign_id}:{occurred.date()}",
                occurred=occurred,
                payload={
                    "campaign_id": campaign_id,
                    "spend_date": occurred.strftime("%Y-%m-%d"),
                    "amount_minor": 250_000 + 10_000 * (week_index % 4),
                    "currency": "GBP",
                    "channel": channel,
                },
                trace=f"campaign:{campaign_id}:{week_index}",
            )
        week_index += 1
        week_start += timedelta(days=7)
