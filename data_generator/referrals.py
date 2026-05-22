from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl

from data_generator.config import (
    REGION_BEHAVIOUR,
    REGIONS,
    TREATED_REFERRAL_REGIONS,
    GeneratorConfig,
)
from data_generator.utils import date_range_days, month_end


def generate_referrals(
    users: pl.DataFrame,
    activation: pl.DataFrame,
    config: GeneratorConfig,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    rng = np.random.default_rng(config.seed + 53)
    end_date = month_end(config.start_date, config.months)
    intervention_start = config.start_date + timedelta(
        days=int((end_date - config.start_date).days * 0.65)
    )
    activated_users = set(
        activation.filter(pl.col("activated_ever_ground_truth")).get_column("user_id").to_list()
    )

    referrer_pool: dict[str, list[str]] = {region: [] for region in REGIONS}
    rows: list[dict[str, object]] = []
    referral_id = 1

    sorted_users = users.sort("signup_ts").select(
        "user_id", "signup_ts", "signup_date", "region", "signup_channel"
    )
    for user in sorted_users.iter_rows(named=True):
        region = user["region"]
        signup_date = user["signup_date"]
        pool = referrer_pool[region]
        in_treated_region = region in TREATED_REFERRAL_REGIONS
        in_intervention = in_treated_region and signup_date >= intervention_start

        base_probability = 0.075 * REGION_BEHAVIOUR[region]["referral"]
        if user["signup_channel"] == "word_of_mouth":
            base_probability += 0.12
        if user["signup_channel"] == "business_referral":
            base_probability += 0.06
        referral_probability = base_probability + (0.055 if in_intervention else 0)

        if pool and rng.random() < np.clip(referral_probability, 0.02, 0.42):
            referrer = str(rng.choice(pool))
            is_incremental = bool(in_intervention and rng.random() < config.referral_incrementality)
            rows.append(
                {
                    "referral_id": f"ref_{referral_id:09d}",
                    "referrer_user_id": referrer,
                    "referee_user_id": user["user_id"],
                    "created_at": user["signup_ts"] - timedelta(days=int(rng.integers(0, 8))),
                    "created_date": signup_date,
                    "referrer_region": region,
                    "referee_region": region,
                    "incentive_region_treated": in_treated_region,
                    "incentive_active": in_intervention,
                    "is_incremental_ground_truth": is_incremental,
                    "referrer_reward_gbp": 10 if in_intervention else 0,
                    "referee_reward_gbp": 10 if in_intervention else 0,
                }
            )
            referral_id += 1

        if user["user_id"] in activated_users:
            referrer_pool[region].append(user["user_id"])

    region_daily = _region_daily_signups(users, intervention_start, end_date)
    return pl.DataFrame(rows), region_daily


def _region_daily_signups(
    users: pl.DataFrame,
    intervention_start: date,
    end_date: date,
) -> pl.DataFrame:
    counts = (
        users.group_by(["region", "signup_date"])
        .agg(pl.len().alias("signups"))
        .rename({"signup_date": "date"})
    )
    days = date_range_days(users["signup_date"].min(), end_date)
    scaffold = pl.DataFrame(
        {
            "region": [region for region in REGIONS for _ in days],
            "date": [day for _ in REGIONS for day in days],
        }
    )
    return (
        scaffold.join(counts, on=["region", "date"], how="left")
        .with_columns(
            pl.col("signups").fill_null(0),
            pl.col("region").is_in(TREATED_REFERRAL_REGIONS).alias("treated_region"),
            (pl.col("date") >= intervention_start).alias("post_period"),
            (
                pl.col("region").is_in(TREATED_REFERRAL_REGIONS)
                & (pl.col("date") >= intervention_start)
            ).alias("incentive_active"),
        )
        .sort(["region", "date"])
    )
