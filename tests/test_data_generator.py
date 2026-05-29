from datetime import date

import polars as pl

from data_generator.config import GeneratorConfig
from data_generator.generate import build_dataset, write_dataset


def test_generator_writes_expected_parquet_files(tmp_path) -> None:
    config = GeneratorConfig(users=500, months=3, start_date=date(2025, 1, 1), seed=123)
    frames = build_dataset(config)
    write_dataset(frames, tmp_path)

    expected = {
        "users",
        "experiment_assignments",
        "activation_ground_truth",
        "transactions",
        "sessions",
        "feature_events",
        "support_contacts",
        "referrals",
        "region_daily_signups",
        "pricing_offer_catalog",
        "pricing_exposures",
        "pricing_outcomes",
        "experiment_ground_truth",
    }
    assert {path.stem for path in tmp_path.glob("*.parquet")} == expected
    assert frames["users"].height == 500
    assert frames["experiment_assignments"].height == 500
    assert frames["activation_ground_truth"].height == 500
    assert frames["pricing_offer_catalog"].height == 4
    assert frames["pricing_exposures"].height > 0
    assert frames["pricing_outcomes"].height == frames["pricing_exposures"].height


def test_generator_is_deterministic_for_same_seed() -> None:
    config = GeneratorConfig(users=200, months=2, start_date=date(2025, 1, 1), seed=999)
    first = build_dataset(config)
    second = build_dataset(config)

    assert first["users"].select("user_id", "signup_ts", "region").equals(
        second["users"].select("user_id", "signup_ts", "region")
    )
    assert first["experiment_assignments"].select("user_id", "variant").equals(
        second["experiment_assignments"].select("user_id", "variant")
    )


def test_business_invariants_hold() -> None:
    config = GeneratorConfig(users=800, months=4, start_date=date(2025, 1, 1), seed=321)
    frames = build_dataset(config)
    users = frames["users"]
    transactions = frames["transactions"]
    activation = frames["activation_ground_truth"]
    pricing_exposures = frames["pricing_exposures"]
    pricing_outcomes = frames["pricing_outcomes"]

    assert users.get_column("age").min() >= 18
    assert transactions.get_column("amount_gbp").min() > 0

    tx_with_signup = transactions.join(
        users.select("user_id", "signup_ts"),
        on="user_id",
        how="left",
    )
    assert tx_with_signup.filter(pl.col("occurred_at") < pl.col("signup_ts")).height == 0

    activation_with_signup = activation.join(
        users.select("user_id", "signup_ts"),
        on="user_id",
        how="left",
    )
    assert (
        activation_with_signup.filter(
            pl.col("activated_d7_ground_truth")
            & (
                pl.col("first_transaction_ts_ground_truth")
                > pl.col("signup_ts") + pl.duration(days=7)
            )
        ).height
        == 0
    )
    assert pricing_exposures.get_column("displayed_incentive_value_gbp").min() >= 0
    assert pricing_outcomes.get_column("gross_margin_30d_gbp").min() >= 0
