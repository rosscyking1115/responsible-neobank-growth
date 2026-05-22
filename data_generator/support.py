from __future__ import annotations

from datetime import datetime, time, timedelta

import numpy as np
import polars as pl

from data_generator.config import REGION_BEHAVIOUR, SUPPORT_TOPICS, GeneratorConfig
from data_generator.utils import month_end


def generate_support_contacts(users: pl.DataFrame, config: GeneratorConfig) -> pl.DataFrame:
    rng = np.random.default_rng(config.seed + 41)
    end_dt = datetime.combine(month_end(config.start_date, config.months), time.max)
    rows: list[dict[str, object]] = []
    contact_id = 1

    for user in users.select(
        "user_id",
        "signup_ts",
        "region",
        "vulnerable_customer_flag",
        "business_account_flag",
    ).iter_rows(named=True):
        base_rate = 0.045 * REGION_BEHAVIOUR[user["region"]]["support"]
        if user["vulnerable_customer_flag"]:
            base_rate += 0.075
        if user["business_account_flag"]:
            base_rate += 0.025
        contact_count = int(rng.poisson(base_rate))
        if rng.random() < base_rate:
            contact_count += 1

        for _ in range(contact_count):
            contact_ts = user["signup_ts"] + timedelta(
                days=int(rng.integers(0, max(1, min((end_dt - user["signup_ts"]).days, 120)))),
                seconds=int(rng.integers(0, 86_400)),
            )
            if contact_ts > end_dt:
                continue
            topic = str(
                rng.choice(
                    SUPPORT_TOPICS,
                    p=[0.24, 0.20, 0.18, 0.10, 0.18, 0.10],
                )
            )
            rows.append(
                {
                    "support_contact_id": f"sup_{contact_id:09d}",
                    "user_id": user["user_id"],
                    "contact_ts": contact_ts,
                    "contact_date": contact_ts.date(),
                    "region": user["region"],
                    "topic": topic,
                    "is_complaint": bool(
                        rng.random() < (0.12 if topic == "fraud_review" else 0.045)
                    ),
                    "resolved_first_contact": bool(rng.random() < 0.72),
                }
            )
            contact_id += 1

    return pl.DataFrame(rows)
