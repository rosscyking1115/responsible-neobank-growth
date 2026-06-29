"""Synthetic customer-protection (scam-intervention) events.

Generates transfer-level risk events with the signals a scam-intervention layer would
see. These feed a *supportive* intervention simulation, not a fraud engine.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import polars as pl

from data_generator.config import GeneratorConfig
from data_generator.utils import month_end

PROTECTION_SEED_OFFSET = 303
PROTECTION_EVENT_SHARE = 0.30  # share of users with a protection-relevant transfer


def generate_protection_events(users: pl.DataFrame, config: GeneratorConfig) -> pl.DataFrame:
    """One row per protection-relevant transfer event."""

    rng = np.random.default_rng(config.seed + PROTECTION_SEED_OFFSET)
    n_users = users.height
    n_events = max(1, int(n_users * PROTECTION_EVENT_SHARE))

    user_index = rng.integers(0, n_users, size=n_events)
    user_id = users.get_column("user_id").to_numpy()[user_index]
    vulnerable = (
        users.get_column("vulnerable_customer_flag").to_numpy()[user_index].astype(bool)
    )

    end_date = month_end(config.start_date, config.months)
    span_days = max((end_date - config.start_date).days, 1)
    event_dates = [
        config.start_date + timedelta(days=int(offset))
        for offset in rng.integers(0, span_days + 1, size=n_events)
    ]

    first_large_transfer = rng.random(n_events) < 0.15
    base_amount = rng.exponential(300.0, size=n_events) + 10.0
    amount_gbp = np.where(first_large_transfer, base_amount * 5.0, base_amount).round(2)

    new_payee = rng.random(n_events) < 0.35
    unusual_time = rng.random(n_events) < 0.20
    recent_device_change = rng.random(n_events) < 0.10
    viewed_scam_warning = rng.random(n_events) < 0.50
    ignored_warning = viewed_scam_warning & (rng.random(n_events) < 0.30)
    confirmed_transfer = rng.random(n_events) < 0.60
    support_contact_about_scam = rng.random(n_events) < np.where(vulnerable, 0.10, 0.05)
    investment_context = rng.random(n_events) < 0.08

    return pl.DataFrame(
        {
            "protection_event_id": [f"prot_{i:07d}" for i in range(1, n_events + 1)],
            "user_id": user_id,
            "event_date": event_dates,
            "amount_gbp": amount_gbp,
            "new_payee": new_payee,
            "first_large_transfer": first_large_transfer,
            "unusual_time": unusual_time,
            "recent_device_change": recent_device_change,
            "viewed_scam_warning": viewed_scam_warning,
            "ignored_warning": ignored_warning,
            "confirmed_transfer": confirmed_transfer,
            "support_contact_about_scam": support_contact_about_scam,
            "investment_context": investment_context,
            "vulnerable_customer": vulnerable,
        }
    )
