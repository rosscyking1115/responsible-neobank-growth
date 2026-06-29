from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from data_generator.config import GeneratorConfig
from data_generator.onboarding import generate_onboarding_events
from data_generator.users import generate_users
from data_generator.wellbeing import generate_wellbeing_proxies
from src.inclusion import (
    abandonment_by_segment,
    assisted_onboarding_segments,
    funnel_conversion,
)


def _config(users: int = 2000) -> GeneratorConfig:
    return GeneratorConfig(users=users, months=3, start_date=date(2025, 1, 1), seed=7)


def _onboarding():
    config = _config()
    users = generate_users(config)
    wellbeing = generate_wellbeing_proxies(users, config)
    return users, generate_onboarding_events(users, wellbeing, config)


# --- generator --------------------------------------------------------------


def test_onboarding_events_align_and_are_monotonic() -> None:
    users, onboarding = _onboarding()
    assert onboarding.height == users.height
    frame = onboarding.to_pandas()
    # The funnel is monotonic: passing implies started, activating implies passing.
    assert (~frame["identity_check_passed"] | frame["identity_check_started"]).all()
    assert (~frame["card_activated"] | frame["identity_check_passed"]).all()
    assert (frame["completed_onboarding"] == frame["card_activated"]).all()


def test_onboarding_generation_is_deterministic() -> None:
    config = _config(users=500)
    users = generate_users(config)
    wellbeing = generate_wellbeing_proxies(users, config)
    first = generate_onboarding_events(users, wellbeing, config)
    second = generate_onboarding_events(users, wellbeing, config)
    assert first.equals(second)


def test_completed_users_have_no_abandoned_step() -> None:
    _, onboarding = _onboarding()
    frame = onboarding.to_pandas()
    completed = frame[frame["completed_onboarding"]]
    assert completed["abandoned_step"].isna().all()


# --- funnel analysis --------------------------------------------------------


def _funnel_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "digital_confidence_band": ["low"] * 50 + ["high"] * 50,
            "identity_check_started": [True] * 40 + [False] * 10 + [True] * 50,
            "identity_check_passed": [True] * 30 + [False] * 20 + [True] * 48 + [False] * 2,
            "card_activated": [True] * 20 + [False] * 30 + [True] * 45 + [False] * 5,
            "completed_onboarding": [True] * 20 + [False] * 30 + [True] * 45 + [False] * 5,
            "needs_assisted_onboarding": [False] * 20 + [True] * 30 + [False] * 50,
        }
    )


def test_funnel_conversion_is_monotonically_non_increasing() -> None:
    funnel = funnel_conversion(_funnel_frame())
    reached = funnel["reached"].tolist()
    assert reached == sorted(reached, reverse=True)
    assert funnel.iloc[0]["step"] == "signup_started"
    assert funnel.iloc[0]["reached"] == 100


def test_abandonment_by_segment_orders_worst_first() -> None:
    summary = abandonment_by_segment(_funnel_frame(), "digital_confidence_band")
    assert summary.iloc[0]["level"] == "low"  # 60% abandon
    assert summary.iloc[0]["abandonment_rate"] == pytest.approx(0.60)
    assert summary.iloc[-1]["level"] == "high"  # 10% abandon


def test_assisted_onboarding_flags_high_abandonment_segments() -> None:
    flags = assisted_onboarding_segments(
        _funnel_frame(), "digital_confidence_band", max_acceptable_abandonment=0.25
    )
    levels = {flag.level for flag in flags}
    assert "low" in levels
    assert "high" not in levels


def test_abandonment_by_segment_rejects_missing_column() -> None:
    with pytest.raises(KeyError):
        abandonment_by_segment(_funnel_frame(), "missing")


# --- dashboard helpers ------------------------------------------------------


def test_dashboard_funnel_helpers() -> None:
    from app.dashboard_data import (
        onboarding_abandonment_by_segment,
        onboarding_funnel_steps,
    )

    funnel = onboarding_funnel_steps(_funnel_frame())
    assert funnel.iloc[0]["reached"] == 100
    abandonment = onboarding_abandonment_by_segment(
        _funnel_frame(), "digital_confidence_band"
    )
    assert abandonment.iloc[0]["level"] == "low"
