import numpy as np
import pandas as pd

from src.experiments.analysis import (
    cuped_adjusted_effect,
    difference_in_means,
    sample_ratio_mismatch,
)
from src.experiments.guardrails import GuardrailSpec, evaluate_guardrail
from src.experiments.power import binary_mde, sample_size_per_arm_binary
from src.experiments.run_onboarding_ab import analyse_onboarding_experiment, render_markdown


def _experiment_frame() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    n = 2_000
    variants = np.array(["control"] * 1_000 + ["treatment"] * 1_000)
    propensity = rng.uniform(0.25, 0.85, size=n)
    outcomes = rng.binomial(1, np.clip(propensity + (variants == "treatment") * 0.04, 0, 1))
    return pd.DataFrame(
        {
            "experiment_name": "personalised_onboarding_pot_prompt",
            "user_id": [f"user_{i:04d}" for i in range(n)],
            "variant": variants,
            "activated_d7": outcomes,
            "d7_activation_probability_control": propensity,
            "signup_channel": np.where(propensity > 0.55, "word_of_mouth", "paid_social"),
            "income_segment": np.where(propensity > 0.65, "high", "middle"),
            "region": np.where(propensity > 0.5, "London", "North West"),
            "device_os": np.where(rng.random(n) > 0.5, "ios", "android"),
            "support_contacts": rng.binomial(1, 0.08, size=n),
            "complaints": rng.binomial(1, 0.01, size=n),
            "app_crashes": rng.binomial(1, 0.03, size=n),
            "vulnerable_customer_flag": rng.binomial(1, 0.05, size=n),
            "activated_ever": outcomes,
            "adopted_savings_pot": outcomes,
            "adopted_salary_sorter": outcomes,
            "push_opt_in": rng.binomial(1, 0.6, size=n),
            "business_account_flag": rng.binomial(1, 0.1, size=n),
        }
    )


def test_difference_in_means_recovers_treatment_minus_control() -> None:
    frame = pd.DataFrame(
        {
            "variant": ["control", "control", "treatment", "treatment"],
            "metric": [0, 1, 1, 1],
        }
    )

    estimate = difference_in_means(frame, "metric")

    assert estimate.control_mean == 0.5
    assert estimate.treatment_mean == 1.0
    assert estimate.effect == 0.5


def test_srm_flags_balanced_assignment_as_passed() -> None:
    frame = pd.DataFrame({"variant": ["control"] * 500 + ["treatment"] * 500})

    result = sample_ratio_mismatch(frame)

    assert result.passed
    assert result.p_value == 1.0


def test_cuped_reduces_variance_with_predictive_covariate() -> None:
    frame = _experiment_frame()

    result = cuped_adjusted_effect(
        frame,
        "activated_d7",
        "d7_activation_probability_control",
    )

    assert result.theta > 0
    assert result.variance_reduction > 0
    assert result.estimate.control_n == int((frame["variant"] == "control").sum())
    assert result.estimate.treatment_n == int((frame["variant"] == "treatment").sum())


def test_guardrail_uses_confidence_bound() -> None:
    frame = pd.DataFrame(
        {
            "variant": ["control"] * 500 + ["treatment"] * 500,
            "has_complaint": [0] * 500 + [0] * 498 + [1, 1],
        }
    )

    result = evaluate_guardrail(
        frame,
        GuardrailSpec("has_complaint", "Complaint rate", max_allowed_increase=0.02),
    )

    assert result.passed


def test_power_helpers_are_positive_and_monotonic() -> None:
    mde_small = binary_mde(0.55, 5_000, 5_000)
    mde_large = binary_mde(0.55, 10_000, 10_000)

    assert mde_small > mde_large > 0
    assert sample_size_per_arm_binary(0.55, 0.02) > 0


def test_onboarding_analysis_renders_ship_or_hold_memo() -> None:
    frame = _experiment_frame()

    analysis = analyse_onboarding_experiment(frame, true_lift_pp=0.03)
    memo = render_markdown(analysis)

    assert "Decision Memo: Personalised Onboarding A/B Test" in memo
    assert "CUPED" in memo
    assert analysis.row_count == len(frame)
