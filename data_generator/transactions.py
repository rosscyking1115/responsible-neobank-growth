from __future__ import annotations

from datetime import datetime, time, timedelta

import numpy as np
import polars as pl

from data_generator.config import (
    INCOME_SEGMENTS,
    MERCHANT_CATEGORIES,
    MERCHANT_CATEGORY_WEIGHTS,
    GeneratorConfig,
)
from data_generator.utils import month_end


def _transaction_amounts(rng: np.random.Generator, categories: np.ndarray) -> np.ndarray:
    base = rng.lognormal(mean=2.75, sigma=0.75, size=len(categories))
    multipliers = {
        "groceries": 1.4,
        "transport": 0.6,
        "eating_out": 1.0,
        "bills": 2.6,
        "shopping": 1.8,
        "travel": 4.0,
        "entertainment": 0.9,
        "cash": 1.2,
    }
    return np.round([base[i] * multipliers[categories[i]] for i in range(len(categories))], 2)


def generate_transactions(
    users: pl.DataFrame,
    experiments: pl.DataFrame,
    config: GeneratorConfig,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    rng = np.random.default_rng(config.seed + 11)
    end_dt = datetime.combine(month_end(config.start_date, config.months), time.max)
    assignments = dict(experiments.select("user_id", "variant").iter_rows())
    rows: list[dict[str, object]] = []
    activation_rows: list[dict[str, object]] = []
    tx_id = 1

    user_iter = users.select(
        "user_id",
        "signup_ts",
        "region",
        "income_segment",
        "d7_activation_probability_control",
        "primary_bank_propensity",
        "vulnerable_customer_flag",
    ).iter_rows(named=True)

    for user in user_iter:
        variant = assignments[user["user_id"]]
        p_d7 = user["d7_activation_probability_control"] + (
            config.d7_treatment_lift if variant == "treatment" else 0
        )
        p_d7 = float(np.clip(p_d7, 0.05, 0.94))
        activated_d7 = bool(rng.random() < p_d7)
        activated_late = bool((not activated_d7) and (rng.random() < 0.18))

        if activated_d7:
            first_lag_days = min(float(rng.lognormal(mean=0.55, sigma=0.75)), 6.9)
        elif activated_late:
            first_lag_days = float(rng.uniform(8, 45))
        else:
            first_lag_days = None

        first_transaction_ts = None
        if first_lag_days is not None:
            first_transaction_ts = user["signup_ts"] + timedelta(
                days=first_lag_days,
                seconds=int(rng.integers(0, 3_600)),
            )
            if first_transaction_ts > end_dt:
                first_transaction_ts = None

        activation_rows.append(
            {
                "user_id": user["user_id"],
                "variant": variant,
                "activated_d7_ground_truth": activated_d7,
                "activated_ever_ground_truth": first_transaction_ts is not None,
                "first_transaction_ts_ground_truth": first_transaction_ts,
                "d7_activation_probability": p_d7,
            }
        )

        if first_transaction_ts is None:
            continue

        income_multiplier = 0.75 + 0.18 * INCOME_SEGMENTS.index(user["income_segment"])
        engagement = float(user["primary_bank_propensity"]) * income_multiplier
        weeks_available = max(1, int((end_dt - first_transaction_ts).days // 7) + 1)
        churn_hazard = 0.035 + (0.035 if user["vulnerable_customer_flag"] else 0)

        for week in range(weeks_available):
            week_start = first_transaction_ts + timedelta(days=7 * week)
            if week_start > end_dt:
                break
            if week > 3 and rng.random() < min(0.85, churn_hazard * np.sqrt(week)):
                break
            mean_txns = np.clip(0.6 + 3.2 * engagement * np.exp(-0.006 * week), 0.15, 6.0)
            weekly_count = int(rng.negative_binomial(2, 2 / (2 + mean_txns)))
            if week == 0:
                weekly_count = max(1, weekly_count)
            if weekly_count == 0:
                continue

            categories = rng.choice(
                MERCHANT_CATEGORIES,
                size=weekly_count,
                p=MERCHANT_CATEGORY_WEIGHTS,
            )
            amounts = _transaction_amounts(rng, categories)
            for category, amount in zip(categories, amounts, strict=True):
                occurred_at = week_start + timedelta(
                    days=int(rng.integers(0, 7)),
                    seconds=int(rng.integers(0, 86_400)),
                )
                if occurred_at > end_dt:
                    continue
                rows.append(
                    {
                        "transaction_id": f"txn_{tx_id:09d}",
                        "user_id": user["user_id"],
                        "occurred_at": occurred_at,
                        "occurred_date": occurred_at.date(),
                        "region": user["region"],
                        "merchant_category": str(category),
                        "amount_gbp": float(amount),
                        "is_card_transaction": True,
                        "interchange_revenue_gbp": round(float(amount) * 0.002, 4),
                    }
                )
                tx_id += 1

    return pl.DataFrame(rows), pl.DataFrame(activation_rows)
