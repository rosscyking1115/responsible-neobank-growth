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


def _large_customer_outcomes(n_per_band: int = 40) -> pd.DataFrame:
    """A frame big enough to clear the default minimum segment size, with a stark
    100pp activation gap between digital-confidence bands."""
    return pd.DataFrame(
        {
            "digital_confidence_band": ["low"] * n_per_band + ["high"] * n_per_band,
            "activated_d7": [False] * n_per_band + [True] * n_per_band,
            "has_support_contact": [False] * (2 * n_per_band),
            "has_complaint": [False] * (2 * n_per_band),
        }
    )


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


def test_release_decision_blocks_on_large_fairness_gap() -> None:
    decision = onboarding_release_decision(
        _experiment_variants(), _large_customer_outcomes()
    )
    # The synthetic outcomes carry a 100pp activation gap -> block dominates.
    assert decision is not None
    assert decision.decision == "block"


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
