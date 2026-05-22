from __future__ import annotations

from datetime import datetime, time

import polars as pl

from data_generator.config import GeneratorConfig
from data_generator.utils import month_end, stable_bucket


def assign_onboarding_experiment(users: pl.DataFrame, config: GeneratorConfig) -> pl.DataFrame:
    end_dt = datetime.combine(month_end(config.start_date, config.months), time.max)
    rows = []
    for user_id, signup_ts in users.select("user_id", "signup_ts").iter_rows():
        bucket = stable_bucket(f"onboarding_prompt::{user_id}")
        variant = "treatment" if bucket >= 5_000 else "control"
        rows.append(
            {
                "experiment_name": "personalised_onboarding_pot_prompt",
                "user_id": user_id,
                "variant": variant,
                "assignment_bucket": bucket,
                "assigned_at": signup_ts,
                "experiment_start_ts": signup_ts,
                "experiment_end_ts": min(signup_ts.replace(hour=23, minute=59, second=59), end_dt),
                "true_d7_lift_pp": config.d7_treatment_lift if variant == "treatment" else 0.0,
            }
        )
    return pl.DataFrame(rows)


def experiment_ground_truth(config: GeneratorConfig) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "metric": [
                "personalised_onboarding_d7_activation_lift_pp",
                "referral_incrementality_fraction",
            ],
            "value": [config.d7_treatment_lift, config.referral_incrementality],
            "description": [
                "Absolute treatment lift embedded in D7 activation probability.",
                "Fraction of incentive-period referral signups that are truly incremental.",
            ],
        }
    )
