from __future__ import annotations

from datetime import datetime, time, timedelta

import numpy as np
import polars as pl

from data_generator.config import (
    CHANNEL_ACTIVATION_EFFECT,
    DEVICE_OS,
    DEVICE_WEIGHTS,
    INCOME_EFFECT,
    INCOME_SEGMENT_WEIGHTS,
    INCOME_SEGMENTS,
    REGION_BEHAVIOUR,
    REGION_WEIGHTS,
    REGIONS,
    SIGNUP_CHANNEL_WEIGHTS,
    SIGNUP_CHANNELS,
    GeneratorConfig,
)
from data_generator.utils import month_end


def generate_users(config: GeneratorConfig) -> pl.DataFrame:
    rng = np.random.default_rng(config.seed)
    end_date = month_end(config.start_date, config.months)
    n_days = (end_date - config.start_date).days + 1
    day_index = np.arange(n_days)

    trend = np.linspace(0.75, 1.35, n_days)
    seasonality = 1 + 0.15 * np.sin(2 * np.pi * day_index / 30.5)
    referral_spike = np.ones(n_days)
    for spike_day in [int(n_days * 0.20), int(n_days * 0.52), int(n_days * 0.80)]:
        referral_spike += 0.45 * np.exp(-0.5 * ((day_index - spike_day) / 5) ** 2)
    day_weights = trend * seasonality * referral_spike
    day_weights = day_weights / day_weights.sum()

    signup_day_offsets = rng.choice(day_index, size=config.users, p=day_weights)
    signup_seconds = rng.integers(0, 86_400, size=config.users)
    start_dt = datetime.combine(config.start_date, time.min)
    signup_ts = [
        start_dt + timedelta(days=int(day), seconds=int(second))
        for day, second in zip(signup_day_offsets, signup_seconds, strict=True)
    ]

    regions = rng.choice(REGIONS, size=config.users, p=REGION_WEIGHTS)
    channels = rng.choice(SIGNUP_CHANNELS, size=config.users, p=SIGNUP_CHANNEL_WEIGHTS)
    devices = rng.choice(DEVICE_OS, size=config.users, p=DEVICE_WEIGHTS)
    income_segments = rng.choice(INCOME_SEGMENTS, size=config.users, p=INCOME_SEGMENT_WEIGHTS)
    age = np.clip(rng.normal(35, 11, size=config.users).round(), 18, 78).astype(int)
    push_opt_in = rng.random(config.users) < np.where(devices == "ios", 0.72, 0.62)
    vulnerable_customer_flag = rng.random(config.users) < np.where(
        income_segments == "low",
        0.09,
        0.035,
    )
    business_account_flag = rng.random(config.users) < np.where(
        channels == "business_referral",
        0.42,
        0.06,
    )

    activation_score = np.array(
        [
            0.50
            + CHANNEL_ACTIVATION_EFFECT[channel]
            + INCOME_EFFECT[income]
            + (REGION_BEHAVIOUR[region]["activation"] - 1) * 0.40
            + (0.035 if push else -0.015)
            + (-0.025 if vulnerable else 0)
            + (0.035 if business else 0)
            for channel, income, region, push, vulnerable, business in zip(
                channels,
                income_segments,
                regions,
                push_opt_in,
                vulnerable_customer_flag,
                business_account_flag,
                strict=True,
            )
        ]
    )
    d7_activation_probability_control = np.clip(activation_score, 0.12, 0.88)
    primary_bank_propensity = np.clip(
        d7_activation_probability_control
        + np.where(income_segments == "affluent", 0.08, 0)
        + np.where(channels == "word_of_mouth", 0.05, 0)
        - np.where(vulnerable_customer_flag, 0.05, 0),
        0.05,
        0.92,
    )

    return pl.DataFrame(
        {
            "user_id": [f"user_{i:06d}" for i in range(1, config.users + 1)],
            "signup_ts": signup_ts,
            "signup_date": [ts.date() for ts in signup_ts],
            "signup_month": [ts.strftime("%Y-%m") for ts in signup_ts],
            "region": regions,
            "signup_channel": channels,
            "device_os": devices,
            "age": age,
            "income_segment": income_segments,
            "push_opt_in": push_opt_in,
            "vulnerable_customer_flag": vulnerable_customer_flag,
            "business_account_flag": business_account_flag,
            "d7_activation_probability_control": d7_activation_probability_control,
            "primary_bank_propensity": primary_bank_propensity,
        }
    )
