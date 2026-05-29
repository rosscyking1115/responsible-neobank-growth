from __future__ import annotations

from datetime import datetime, time, timedelta

import numpy as np
import polars as pl

from data_generator.config import GeneratorConfig
from data_generator.utils import month_end

OFFER_CATALOG = [
    {
        "offer_id": "easy_access_savings_boost",
        "offer_name": "Easy Access Savings Boost",
        "product_area": "savings",
        "offer_type": "rate_boost",
        "monthly_fee_gbp": 0.0,
        "base_incentive_cost_gbp": 2.0,
        "expected_monthly_margin_gbp": 1.8,
        "vulnerable_customer_eligible": True,
    },
    {
        "offer_id": "premium_bundle_trial",
        "offer_name": "Premium Bundle Trial",
        "product_area": "subscription",
        "offer_type": "fee_trial",
        "monthly_fee_gbp": 5.0,
        "base_incentive_cost_gbp": 4.0,
        "expected_monthly_margin_gbp": 3.6,
        "vulnerable_customer_eligible": False,
    },
    {
        "offer_id": "business_account_cashback",
        "offer_name": "Business Account Cashback",
        "product_area": "business_banking",
        "offer_type": "cashback",
        "monthly_fee_gbp": 0.0,
        "base_incentive_cost_gbp": 7.5,
        "expected_monthly_margin_gbp": 5.4,
        "vulnerable_customer_eligible": True,
    },
    {
        "offer_id": "low_cost_referral_reward",
        "offer_name": "Low-Cost Referral Reward",
        "product_area": "growth",
        "offer_type": "referral_incentive",
        "monthly_fee_gbp": 0.0,
        "base_incentive_cost_gbp": 5.0,
        "expected_monthly_margin_gbp": 2.7,
        "vulnerable_customer_eligible": True,
    },
]


def _catalog_by_offer() -> dict[str, dict[str, object]]:
    return {offer["offer_id"]: offer for offer in OFFER_CATALOG}


def _eligible_offers(user: dict[str, object]) -> list[str]:
    offers = ["easy_access_savings_boost", "premium_bundle_trial", "low_cost_referral_reward"]
    if user["business_account_flag"]:
        offers.append("business_account_cashback")
    if user["vulnerable_customer_flag"]:
        offers = [
            offer
            for offer in offers
            if bool(_catalog_by_offer()[offer]["vulnerable_customer_eligible"])
        ]
    return offers


def _offer_weights(offers: list[str], *, business_account: bool) -> np.ndarray:
    base_weights = {
        "easy_access_savings_boost": 0.34,
        "premium_bundle_trial": 0.24,
        "business_account_cashback": 0.18 if business_account else 0.03,
        "low_cost_referral_reward": 0.24,
    }
    weights = np.array([base_weights[offer] for offer in offers], dtype=float)
    return weights / weights.sum()


def generate_pricing(
    users: pl.DataFrame,
    activation: pl.DataFrame,
    config: GeneratorConfig,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    rng = np.random.default_rng(config.seed + 71)
    end_dt = datetime.combine(month_end(config.start_date, config.months), time.max)
    activation_lookup = {
        row["user_id"]: row
        for row in activation.select(
            "user_id",
            "activated_ever_ground_truth",
        ).iter_rows(named=True)
    }
    catalog = _catalog_by_offer()
    exposure_rows: list[dict[str, object]] = []
    outcome_rows: list[dict[str, object]] = []
    exposure_id = 1

    user_iter = users.select(
        "user_id",
        "signup_ts",
        "signup_date",
        "region",
        "income_segment",
        "primary_bank_propensity",
        "vulnerable_customer_flag",
        "business_account_flag",
    ).iter_rows(named=True)

    income_effect = {
        "student": -0.04,
        "low": -0.03,
        "middle": 0.00,
        "high": 0.04,
        "affluent": 0.07,
    }
    offer_base_acceptance = {
        "easy_access_savings_boost": 0.16,
        "premium_bundle_trial": 0.10,
        "business_account_cashback": 0.13,
        "low_cost_referral_reward": 0.12,
    }

    for user in user_iter:
        activated = bool(activation_lookup[user["user_id"]]["activated_ever_ground_truth"])
        exposure_probability = 0.28 + (0.22 if activated else 0.0)
        exposure_probability += 0.18 * float(user["primary_bank_propensity"])
        if rng.random() > min(0.82, exposure_probability):
            continue

        offers = _eligible_offers(user)
        offer_id = str(
            rng.choice(
                offers,
                p=_offer_weights(offers, business_account=bool(user["business_account_flag"])),
            )
        )
        offer = catalog[offer_id]
        variant = str(rng.choice(["holdout", "standard", "incentive"], p=[0.18, 0.52, 0.30]))
        incentive_multiplier = {"holdout": 0.0, "standard": 0.55, "incentive": 1.0}[variant]
        incentive_value = round(float(offer["base_incentive_cost_gbp"]) * incentive_multiplier, 2)
        exposure_ts = user["signup_ts"] + timedelta(
            days=int(rng.integers(2, 91)),
            seconds=int(rng.integers(0, 86_400)),
        )
        if exposure_ts > end_dt:
            continue

        understanding_required = bool(user["vulnerable_customer_flag"]) or rng.random() < 0.04
        eligibility_reason = (
            "business_eligible"
            if offer_id == "business_account_cashback"
            else "growth_propensity"
            if offer_id == "low_cost_referral_reward"
            else "savings_intent"
            if offer_id == "easy_access_savings_boost"
            else "subscription_propensity"
        )

        exposure_key = f"offer_exp_{exposure_id:09d}"
        exposure_rows.append(
            {
                "exposure_id": exposure_key,
                "user_id": user["user_id"],
                "offer_id": offer_id,
                "exposure_ts": exposure_ts,
                "exposure_date": exposure_ts.date(),
                "price_variant": variant,
                "displayed_monthly_fee_gbp": float(offer["monthly_fee_gbp"]),
                "displayed_incentive_value_gbp": incentive_value,
                "eligibility_reason_code": eligibility_reason,
                "customer_understanding_required": understanding_required,
            }
        )

        accept_probability = (
            offer_base_acceptance[offer_id]
            + 0.12 * float(user["primary_bank_propensity"])
            + income_effect[str(user["income_segment"])]
            + 0.014 * incentive_value
            - 0.025 * float(offer["monthly_fee_gbp"])
            - (0.04 if user["vulnerable_customer_flag"] else 0.0)
            + (
                0.06
                if offer_id == "business_account_cashback" and user["business_account_flag"]
                else 0.0
            )
            - (0.05 if variant == "holdout" else 0.0)
        )
        accepted = bool(rng.random() < float(np.clip(accept_probability, 0.01, 0.68)))
        outcome_ts = exposure_ts + timedelta(days=int(rng.integers(0, 15))) if accepted else None
        gross_margin = (
            round(float(offer["expected_monthly_margin_gbp"]) * float(rng.uniform(0.65, 1.45)), 2)
            if accepted
            else 0.0
        )
        realized_incentive_cost = incentive_value if accepted else 0.0
        support_probability = 0.025 + (0.03 if user["vulnerable_customer_flag"] else 0.0)
        support_probability += 0.01 if incentive_value >= 5 else 0.0
        support_contact = bool(rng.random() < support_probability)
        complaint_probability = 0.10 + (0.08 if user["vulnerable_customer_flag"] else 0.0)
        complaint = bool(support_contact and rng.random() < complaint_probability)

        outcome_rows.append(
            {
                "exposure_id": exposure_key,
                "user_id": user["user_id"],
                "offer_id": offer_id,
                "accepted_offer": accepted,
                "activated_offer": bool(accepted and rng.random() < 0.78),
                "outcome_ts": outcome_ts,
                "gross_margin_30d_gbp": gross_margin,
                "incentive_cost_gbp": realized_incentive_cost,
                "net_margin_30d_gbp": round(gross_margin - realized_incentive_cost, 2),
                "support_contact_14d": support_contact,
                "complaint_14d": complaint,
            }
        )
        exposure_id += 1

    return (
        pl.DataFrame(OFFER_CATALOG),
        pl.DataFrame(exposure_rows),
        pl.DataFrame(outcome_rows),
    )
