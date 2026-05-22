from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class GeneratorConfig:
    users: int = 50_000
    months: int = 12
    start_date: date = date(2025, 1, 1)
    seed: int = 42
    d7_treatment_lift: float = 0.03
    referral_incrementality: float = 0.60


REGIONS = [
    "London",
    "South East",
    "North West",
    "East of England",
    "West Midlands",
    "South West",
    "Yorkshire and The Humber",
    "Scotland",
    "East Midlands",
    "Wales",
    "North East",
    "Northern Ireland",
]

REGION_WEIGHTS = [0.18, 0.13, 0.11, 0.10, 0.09, 0.09, 0.08, 0.07, 0.06, 0.04, 0.03, 0.02]

REGION_BEHAVIOUR = {
    "London": {"activation": 1.08, "referral": 1.10, "support": 0.96},
    "South East": {"activation": 1.04, "referral": 1.02, "support": 0.98},
    "North West": {"activation": 1.00, "referral": 1.04, "support": 1.00},
    "East of England": {"activation": 1.02, "referral": 0.96, "support": 0.98},
    "West Midlands": {"activation": 0.97, "referral": 1.00, "support": 1.03},
    "South West": {"activation": 1.01, "referral": 0.98, "support": 1.00},
    "Yorkshire and The Humber": {"activation": 0.98, "referral": 1.05, "support": 1.02},
    "Scotland": {"activation": 0.99, "referral": 1.01, "support": 1.01},
    "East Midlands": {"activation": 0.96, "referral": 0.97, "support": 1.04},
    "Wales": {"activation": 0.95, "referral": 0.95, "support": 1.05},
    "North East": {"activation": 0.93, "referral": 0.94, "support": 1.07},
    "Northern Ireland": {"activation": 0.94, "referral": 0.92, "support": 1.06},
}

TREATED_REFERRAL_REGIONS = ["North West", "Yorkshire and The Humber", "Wales"]

SIGNUP_CHANNELS = [
    "word_of_mouth",
    "app_store",
    "organic_search",
    "paid_social",
    "partnership",
    "campus",
    "business_referral",
]

SIGNUP_CHANNEL_WEIGHTS = [0.38, 0.18, 0.16, 0.12, 0.07, 0.05, 0.04]

CHANNEL_ACTIVATION_EFFECT = {
    "word_of_mouth": 0.08,
    "app_store": 0.03,
    "organic_search": 0.04,
    "paid_social": -0.04,
    "partnership": 0.02,
    "campus": -0.02,
    "business_referral": 0.06,
}

INCOME_SEGMENTS = ["student", "low", "middle", "high", "affluent"]
INCOME_SEGMENT_WEIGHTS = [0.12, 0.18, 0.42, 0.20, 0.08]

INCOME_EFFECT = {
    "student": -0.04,
    "low": -0.03,
    "middle": 0.00,
    "high": 0.04,
    "affluent": 0.06,
}

DEVICE_OS = ["ios", "android"]
DEVICE_WEIGHTS = [0.58, 0.42]

MERCHANT_CATEGORIES = [
    "groceries",
    "transport",
    "eating_out",
    "bills",
    "shopping",
    "travel",
    "entertainment",
    "cash",
]

MERCHANT_CATEGORY_WEIGHTS = [0.26, 0.14, 0.18, 0.11, 0.14, 0.05, 0.09, 0.03]

FEATURES = ["savings_pot", "easy_access_savings", "salary_sorter", "referrals"]

SUPPORT_TOPICS = [
    "card_delivery",
    "app_help",
    "payment_query",
    "fraud_review",
    "account_limits",
    "vulnerable_customer_support",
]
