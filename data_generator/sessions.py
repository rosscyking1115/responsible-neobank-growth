from __future__ import annotations

from datetime import datetime, time, timedelta

import numpy as np
import polars as pl

from data_generator.config import GeneratorConfig
from data_generator.utils import month_end


def generate_sessions(
    users: pl.DataFrame,
    activation: pl.DataFrame,
    config: GeneratorConfig,
) -> pl.DataFrame:
    rng = np.random.default_rng(config.seed + 23)
    end_dt = datetime.combine(month_end(config.start_date, config.months), time.max)
    activation_lookup = {
        user_id: activated
        for user_id, activated in activation.select(
            "user_id", "activated_ever_ground_truth"
        ).iter_rows()
    }
    rows: list[dict[str, object]] = []
    session_id = 1

    for user in users.select(
        "user_id",
        "signup_ts",
        "region",
        "device_os",
        "primary_bank_propensity",
        "push_opt_in",
    ).iter_rows(named=True):
        is_activated = activation_lookup[user["user_id"]]
        first_week_mean = 4.0 + 7.0 * float(user["primary_bank_propensity"])
        if user["push_opt_in"]:
            first_week_mean += 1.5
        first_week_sessions = int(rng.poisson(first_week_mean))
        ongoing_sessions = int(
            rng.negative_binomial(2, 2 / (2 + (2.5 if is_activated else 0.6)))
        )
        session_count = max(1, first_week_sessions + ongoing_sessions)
        max_days = max(1, min((end_dt - user["signup_ts"]).days, 90))
        mode_day = min(5, max_days)

        for _ in range(session_count):
            day = int(rng.triangular(0, mode_day, max_days))
            started_at = user["signup_ts"] + timedelta(
                days=day,
                seconds=int(rng.integers(0, 86_400)),
            )
            if started_at > end_dt:
                continue
            rows.append(
                {
                    "session_id": f"sess_{session_id:09d}",
                    "user_id": user["user_id"],
                    "started_at": started_at,
                    "started_date": started_at.date(),
                    "region": user["region"],
                    "device_os": user["device_os"],
                    "duration_seconds": int(rng.lognormal(mean=4.7, sigma=0.75)),
                    "app_crashed": bool(rng.random() < 0.006),
                }
            )
            session_id += 1

    return pl.DataFrame(rows)
