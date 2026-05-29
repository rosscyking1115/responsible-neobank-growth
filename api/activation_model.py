"""Serve the persisted activation model when an artifact registry is configured."""

from __future__ import annotations

import os
from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd

from api.schemas import CustomerFeatures
from src.modelling.artifacts import ActivationModelBundle, load_activation_model_artifact

ACTIVATION_REGISTRY_ENV = "NEOBANK_ACTIVATION_MODEL_REGISTRY"


@lru_cache(maxsize=1)
def load_configured_activation_artifact() -> ActivationModelBundle | None:
    registry_value = os.getenv(ACTIVATION_REGISTRY_ENV)
    if not registry_value:
        return None
    registry_path = Path(registry_value)
    if not registry_path.exists():
        return None
    return load_activation_model_artifact(registry_path)


def activation_feature_frame(customer: CustomerFeatures) -> pd.DataFrame:
    signup_date = customer.signup_date or date(2025, 1, 1)
    return pd.DataFrame(
        [
            {
                "region": customer.region,
                "signup_channel": customer.signup_channel,
                "device_os": customer.device_os,
                "age": customer.age,
                "income_segment": customer.income_segment,
                "push_opt_in": int(customer.push_opt_in),
                "vulnerable_customer_flag": int(customer.vulnerable_customer_flag),
                "business_account_flag": int(customer.business_account_flag),
                "signup_month_number": signup_date.month,
                "signup_day_of_week": signup_date.weekday(),
            }
        ]
    )
