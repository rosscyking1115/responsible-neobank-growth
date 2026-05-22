from __future__ import annotations

from datetime import datetime, time, timedelta

import numpy as np
import polars as pl

from data_generator.config import GeneratorConfig
from data_generator.utils import month_end


def generate_feature_usage(
    users: pl.DataFrame,
    activation: pl.DataFrame,
    config: GeneratorConfig,
) -> pl.DataFrame:
    rng = np.random.default_rng(config.seed + 37)
    end_dt = datetime.combine(month_end(config.start_date, config.months), time.max)
    activation_lookup = {
        row["user_id"]: row
        for row in activation.select(
            "user_id", "activated_ever_ground_truth", "first_transaction_ts_ground_truth"
        ).iter_rows(named=True)
    }
    rows: list[dict[str, object]] = []
    event_id = 1

    for user in users.select(
        "user_id",
        "signup_ts",
        "region",
        "income_segment",
        "primary_bank_propensity",
        "business_account_flag",
    ).iter_rows(named=True):
        activation_row = activation_lookup[user["user_id"]]
        if not activation_row["activated_ever_ground_truth"]:
            continue

        first_tx = activation_row["first_transaction_ts_ground_truth"] or user["signup_ts"]
        propensity = float(user["primary_bank_propensity"])
        income_bonus = 0.10 if user["income_segment"] in {"high", "affluent"} else 0.0
        pot_adopted = rng.random() < np.clip(0.22 + 0.42 * propensity + income_bonus, 0.08, 0.78)
        savings_probability = np.clip(0.28 + 0.32 * propensity, 0.05, 0.68)
        savings_adopted = pot_adopted and rng.random() < savings_probability
        salary_adopted = rng.random() < np.clip(
            0.10 + 0.45 * propensity + (0.10 if user["business_account_flag"] else 0),
            0.04,
            0.72,
        )
        referral_opened = rng.random() < np.clip(0.08 + 0.22 * propensity, 0.02, 0.40)

        adoptions = [
            ("savings_pot", pot_adopted, 5, 35),
            ("easy_access_savings", savings_adopted, 10, 70),
            ("salary_sorter", salary_adopted, 14, 80),
            ("referrals", referral_opened, 3, 60),
        ]
        for feature_name, adopted, low_day, high_day in adoptions:
            if not adopted:
                continue
            event_ts = first_tx + timedelta(
                days=int(rng.integers(low_day, high_day + 1)),
                seconds=int(rng.integers(0, 86_400)),
            )
            if event_ts > end_dt:
                continue
            rows.append(
                {
                    "feature_event_id": f"feat_{event_id:09d}",
                    "user_id": user["user_id"],
                    "feature_name": feature_name,
                    "event_type": "adopted",
                    "event_ts": event_ts,
                    "event_date": event_ts.date(),
                    "region": user["region"],
                }
            )
            event_id += 1

    return pl.DataFrame(rows)
