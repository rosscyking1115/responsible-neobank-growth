"""Feature engineering for activation decisioning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

TARGET_COLUMN = "activated_d7"
ID_COLUMNS = ["user_id", "signup_date"]
CATEGORICAL_FEATURES = ["region", "signup_channel", "device_os", "income_segment"]
NUMERIC_FEATURES = ["age", "signup_month_number", "signup_day_of_week"]
BINARY_FEATURES = ["push_opt_in", "vulnerable_customer_flag", "business_account_flag"]
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES + BINARY_FEATURES


@dataclass(frozen=True)
class ModelSplit:
    train: pd.DataFrame
    calibration: pd.DataFrame
    test: pd.DataFrame


def load_activation_frame(db_path: Path) -> pd.DataFrame:
    """Load one row per user with only signup-time model features plus evaluation labels."""

    query = """
        select
            activation.user_id,
            activation.signup_date,
            activation.region,
            activation.signup_channel,
            activation.device_os,
            activation.age,
            activation.income_segment,
            activation.push_opt_in,
            activation.vulnerable_customer_flag,
            activation.business_account_flag,
            activation.activated_d7,
            clv.clv_proxy_12m_gbp
        from main_marts.fct_activation as activation
        left join main_marts.fct_user_clv_proxy as clv
            on activation.user_id = clv.user_id
    """
    with duckdb.connect(str(db_path), read_only=True) as con:
        frame = con.execute(query).fetchdf()
    if frame.empty:
        raise ValueError("No activation rows found in the DuckDB metrics layer")
    return make_activation_features(frame)


def make_activation_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add deterministic signup-time date features and normalize dtypes."""

    prepared = frame.copy()
    prepared["signup_date"] = pd.to_datetime(prepared["signup_date"])
    prepared["signup_month_number"] = prepared["signup_date"].dt.month.astype(int)
    prepared["signup_day_of_week"] = prepared["signup_date"].dt.dayofweek.astype(int)
    prepared[TARGET_COLUMN] = prepared[TARGET_COLUMN].astype(int)
    for column in BINARY_FEATURES:
        prepared[column] = prepared[column].astype(int)
    prepared["clv_proxy_12m_gbp"] = prepared["clv_proxy_12m_gbp"].fillna(0.0).astype(float)
    return prepared


def temporal_train_calibration_test_split(
    frame: pd.DataFrame,
    *,
    train_fraction: float = 0.60,
    calibration_fraction: float = 0.20,
) -> ModelSplit:
    """Split by signup date order to mimic forward-looking model validation."""

    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1")
    if not 0 < calibration_fraction < 1:
        raise ValueError("calibration_fraction must be between 0 and 1")
    if train_fraction + calibration_fraction >= 1:
        raise ValueError("train + calibration fractions must leave a test split")

    ordered = frame.sort_values(["signup_date", "user_id"]).reset_index(drop=True)
    train_end = int(len(ordered) * train_fraction)
    calibration_end = int(len(ordered) * (train_fraction + calibration_fraction))
    return ModelSplit(
        train=ordered.iloc[:train_end].reset_index(drop=True),
        calibration=ordered.iloc[train_end:calibration_end].reset_index(drop=True),
        test=ordered.iloc[calibration_end:].reset_index(drop=True),
    )


def feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[FEATURE_COLUMNS].copy()


def target_vector(frame: pd.DataFrame) -> pd.Series:
    return frame[TARGET_COLUMN].astype(int)


def activated_user_value(frame: pd.DataFrame) -> float:
    activated = frame.loc[frame[TARGET_COLUMN] == 1, "clv_proxy_12m_gbp"]
    if activated.empty:
        return float(frame["clv_proxy_12m_gbp"].mean())
    return float(activated.mean())
