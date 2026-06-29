from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from data_generator.config import GeneratorConfig
from data_generator.users import generate_users
from data_generator.wellbeing import generate_wellbeing_proxies
from src.wellbeing.guardrails import (
    PROHIBITED_USES,
    ProhibitedUseError,
    assert_permitted_use,
    assert_supportive_decision,
    is_permitted_use,
)
from src.wellbeing.metrics import outcome_gap, segment_outcome_rates

SCORE_COLUMNS = [
    "income_volatility_score",
    "salary_regularity_score",
    "cash_buffer_proxy",
    "bill_pressure_score",
    "overdraft_risk_proxy",
    "digital_confidence_score",
]


def _config(users: int = 600) -> GeneratorConfig:
    return GeneratorConfig(users=users, months=3, start_date=date(2025, 1, 1), seed=123)


def _proxies(config: GeneratorConfig):
    users = generate_users(config)
    return users, generate_wellbeing_proxies(users, config)


# --- generator --------------------------------------------------------------


def test_wellbeing_proxies_align_with_users() -> None:
    config = _config()
    users, proxies = _proxies(config)

    assert proxies.height == users.height
    assert proxies.get_column("customer_id").to_list() == users.get_column("user_id").to_list()


def test_wellbeing_scores_are_bounded_probabilities() -> None:
    _, proxies = _proxies(_config())
    for column in SCORE_COLUMNS:
        series = proxies.get_column(column)
        assert series.min() >= 0.0
        assert series.max() <= 1.0


def test_wellbeing_generation_is_deterministic_for_same_seed() -> None:
    config = _config(users=300)
    users = generate_users(config)
    first = generate_wellbeing_proxies(users, config)
    second = generate_wellbeing_proxies(users, config)
    assert first.equals(second)


def test_vulnerable_proxy_is_a_superset_of_source_flag() -> None:
    config = _config()
    users, proxies = _proxies(config)
    source_flag = users.get_column("vulnerable_customer_flag").to_numpy()
    proxy_flag = proxies.get_column("vulnerable_customer_proxy").to_numpy()
    # Every source-flagged customer remains flagged by the proxy.
    assert bool((proxy_flag | ~source_flag).all())


def test_strained_segments_have_higher_overdraft_risk() -> None:
    config = _config(users=4000)
    users, proxies = _proxies(config)
    joined = (
        users.join(proxies.rename({"customer_id": "user_id"}), on="user_id", how="inner")
        .select("income_segment", "overdraft_risk_proxy")
        .to_pandas()
    )
    means = joined.groupby("income_segment")["overdraft_risk_proxy"].mean()
    assert means["low"] > means["affluent"]


# --- guardrails -------------------------------------------------------------


def test_permitted_use_passes() -> None:
    assert_permitted_use("fairness_gap_detection")
    assert is_permitted_use("supportive_onboarding")


@pytest.mark.parametrize("use", sorted(PROHIBITED_USES))
def test_prohibited_uses_raise(use: str) -> None:
    with pytest.raises(ProhibitedUseError):
        assert_permitted_use(use)
    assert not is_permitted_use(use)


def test_unknown_use_raises() -> None:
    with pytest.raises(ProhibitedUseError):
        assert_permitted_use("maximise_revenue")


def test_supportive_decision_guard() -> None:
    assert_supportive_decision("assisted_onboarding")
    with pytest.raises(ProhibitedUseError):
        assert_supportive_decision("close_account")


# --- metrics ----------------------------------------------------------------


def _outcome_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "digital_confidence_band": ["low", "low", "high", "high", "high"],
            "failed_onboarding": [True, True, False, False, False],
            "activated": [False, True, True, True, True],
        }
    )


def test_segment_outcome_rates_computes_means_and_counts() -> None:
    rates = segment_outcome_rates(
        _outcome_frame(), "digital_confidence_band", ["failed_onboarding", "activated"]
    )
    low = rates[rates["level"] == "low"].iloc[0]
    high = rates[rates["level"] == "high"].iloc[0]
    assert low["customers"] == 2
    assert high["customers"] == 3
    assert low["failed_onboarding"] == pytest.approx(1.0)
    assert high["failed_onboarding"] == pytest.approx(0.0)


def test_outcome_gap_reports_worst_and_best_levels() -> None:
    gap = outcome_gap(_outcome_frame(), "digital_confidence_band", "failed_onboarding")
    assert gap is not None
    assert gap.best_level == "low"  # highest failed-onboarding rate
    assert gap.worst_level == "high"
    assert gap.gap == pytest.approx(1.0)


def test_outcome_gap_returns_none_with_single_level() -> None:
    frame = pd.DataFrame({"band": ["a", "a"], "outcome": [1, 0]})
    assert outcome_gap(frame, "band", "outcome") is None


def test_segment_outcome_rates_rejects_missing_columns() -> None:
    with pytest.raises(KeyError):
        segment_outcome_rates(_outcome_frame(), "missing", ["activated"])
