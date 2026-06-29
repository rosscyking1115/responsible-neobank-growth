from __future__ import annotations

import pandas as pd

from app.dashboard_data import (
    customer_outcome_gaps,
    onboarding_release_decision,
)


def _customer_outcomes() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "digital_confidence_band": ["low"] * 4 + ["high"] * 4,
            "activated_d7": [False, False, False, False, True, True, True, True],
            "has_support_contact": [True, True, False, False, False, False, False, False],
            "has_complaint": [False] * 8,
        }
    )


def _experiment_segment_outcomes(*, widen: bool, n: int = 60) -> pd.DataFrame:
    """Variant x income-band activation where the treatment either widens or narrows
    the gap between bands (n users per cell, above the min_cell threshold)."""
    if widen:
        rates = {  # control gap 0pp -> treatment gap 80pp (widens)
            ("control", "high"): 0.5,
            ("control", "low"): 0.5,
            ("treatment", "high"): 0.9,
            ("treatment", "low"): 0.1,
        }
    else:
        rates = {  # control gap 60pp -> treatment gap 10pp (narrows)
            ("control", "high"): 0.8,
            ("control", "low"): 0.2,
            ("treatment", "high"): 0.85,
            ("treatment", "low"): 0.75,
        }
    rows: list[dict[str, object]] = []
    for (variant, band), rate in rates.items():
        activated = int(round(rate * n))
        for i in range(n):
            rows.append(
                {"variant": variant, "income_band": band, "activated_d7": i < activated}
            )
    return pd.DataFrame(rows)


def _experiment_variants(
    *, treatment_support: float = 0.10, treatment_activation: float = 0.45
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "variant": ["control", "treatment"],
            "users": [1000, 1000],
            "d7_activation_rate": [0.40, treatment_activation],
            "support_contact_rate": [0.10, treatment_support],
            "complaint_rate": [0.01, 0.01],
            "app_crash_rate": [0.02, 0.02],
        }
    )


def test_customer_outcome_gaps_ranks_by_disparity() -> None:
    gaps = customer_outcome_gaps(
        _customer_outcomes(),
        segments=["digital_confidence_band"],
        outcomes=["activated_d7", "has_support_contact"],
        min_segment_size=1,
    )
    activation = gaps[gaps["outcome"] == "activated_d7"].iloc[0]
    assert activation["gap_pp"] == 100.0  # low band 0%, high band 100%
    assert activation["higher_rate_level"] == "high"
    assert activation["lower_rate_level"] == "low"


def test_customer_outcome_gaps_empty_frame() -> None:
    gaps = customer_outcome_gaps(pd.DataFrame())
    assert gaps.empty
    assert "gap_pp" in gaps.columns


def test_release_decision_clean_strong_change_ships() -> None:
    decision = onboarding_release_decision(_experiment_variants(), pd.DataFrame())
    assert decision is not None
    assert decision.decision == "ship"


def test_release_decision_downgrades_on_support_burden() -> None:
    variants = _experiment_variants(treatment_support=0.12)  # +2pp support burden (warn)
    decision = onboarding_release_decision(variants, pd.DataFrame())
    assert decision is not None
    assert decision.decision == "limited_rollout"


def test_release_decision_blocks_when_treatment_widens_gap() -> None:
    decision = onboarding_release_decision(
        _experiment_variants(), _experiment_segment_outcomes(widen=True)
    )
    # The treatment widens the segment activation gap -> block dominates.
    assert decision is not None
    assert decision.decision == "block"


def test_release_decision_not_blocked_when_treatment_narrows_gap() -> None:
    # A strong treatment that *reduces* a large baseline disparity must not be blocked.
    decision = onboarding_release_decision(
        _experiment_variants(), _experiment_segment_outcomes(widen=False)
    )
    assert decision is not None
    assert decision.decision == "ship"


def test_release_decision_handles_missing_experiment() -> None:
    assert onboarding_release_decision(pd.DataFrame(), pd.DataFrame()) is None
    incomplete = pd.DataFrame(
        {
            "variant": ["control"],
            "users": [10],
            "d7_activation_rate": [0.4],
            "support_contact_rate": [0.1],
            "complaint_rate": [0.0],
        }
    )
    assert onboarding_release_decision(incomplete, pd.DataFrame()) is None
