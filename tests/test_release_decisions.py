from __future__ import annotations

import pytest

from src.release_decisions import ReleaseSignals, decide
from src.release_decisions.report import render_decision_markdown
from src.release_decisions.thresholds import ReleaseThresholds


def _clean_signals(**overrides) -> ReleaseSignals:
    """A strong, clean change that should ship unless overridden."""
    base = {
        "feature_name": "personalised_onboarding",
        "business_uplift": 0.031,
        "evidence_strength": 0.9,
        "incrementality_confirmed": True,
        "experiment_valid": True,
        "complaint_rate_delta": 0.0,
        "support_burden_delta": 0.0,
        "fairness_gap": 0.0,
        "vulnerable_customer_impact": 0.0,
        "fair_value_score": 0.9,
        "model_calibration_error": 0.02,
        "model_drift_psi": 0.02,
        "data_quality_ok": True,
        "human_review_load": 0.2,
    }
    base.update(overrides)
    return ReleaseSignals(**base)


def test_strong_clean_change_ships() -> None:
    decision = decide(_clean_signals())
    assert decision.decision == "ship"
    assert decision.evidence_tier == "ship"
    assert decision.is_actionable


def test_harm_signal_blocks_even_with_strong_uplift() -> None:
    decision = decide(_clean_signals(business_uplift=0.20, complaint_rate_delta=0.02))
    assert decision.decision == "block"
    assert not decision.is_actionable
    assert any("complaint" in reason for reason in decision.reasons)


def test_fairness_gap_block_dominates() -> None:
    decision = decide(_clean_signals(fairness_gap=0.15))
    assert decision.decision == "block"


def test_data_quality_failure_blocks() -> None:
    assert decide(_clean_signals(data_quality_ok=False)).decision == "block"


def test_vulnerable_impact_triggers_human_review() -> None:
    decision = decide(_clean_signals(vulnerable_customer_impact=-0.015))
    assert decision.decision == "needs_human_review"


def test_high_review_load_triggers_human_review() -> None:
    assert decide(_clean_signals(human_review_load=0.9)).decision == "needs_human_review"


def test_block_outranks_review() -> None:
    # Both a review-level and a block-level concern present -> block wins.
    decision = decide(
        _clean_signals(vulnerable_customer_impact=-0.015, data_quality_ok=False)
    )
    assert decision.decision == "block"


def test_weak_evidence_is_experiment_only() -> None:
    decision = decide(_clean_signals(evidence_strength=0.4))
    assert decision.decision == "experiment_only"
    assert decision.evidence_tier == "insufficient"


def test_non_incremental_is_experiment_only() -> None:
    assert decide(_clean_signals(incrementality_confirmed=False)).decision == "experiment_only"


def test_invalid_experiment_is_experiment_only() -> None:
    assert decide(_clean_signals(experiment_valid=False)).decision == "experiment_only"


def test_negative_uplift_is_experiment_only() -> None:
    assert decide(_clean_signals(business_uplift=-0.01)).decision == "experiment_only"


def test_warn_level_guardrail_downgrades_ship_to_limited_rollout() -> None:
    decision = decide(_clean_signals(support_burden_delta=0.015))
    assert decision.decision == "limited_rollout"
    assert any("support" in reason for reason in decision.reasons)


def test_rollout_grade_evidence_is_limited_rollout() -> None:
    # Clean guardrails but evidence only rollout-grade (between rollout and ship).
    decision = decide(_clean_signals(evidence_strength=0.7))
    assert decision.evidence_tier == "rollout"
    assert decision.decision == "limited_rollout"


def test_thresholds_are_configurable() -> None:
    strict = ReleaseThresholds(ship_evidence_strength=0.95)
    decision = decide(_clean_signals(evidence_strength=0.9), strict)
    assert decision.decision == "limited_rollout"


def test_report_renders_headline_and_checks() -> None:
    markdown = render_decision_markdown(decide(_clean_signals()))
    assert "Release decision: SHIP" in markdown
    assert "complaint_risk" in markdown
    assert "| Check | Status | Detail |" in markdown


@pytest.mark.parametrize(
    "decision_obj",
    [
        decide(_clean_signals()),
        decide(_clean_signals(complaint_rate_delta=0.02)),
        decide(_clean_signals(evidence_strength=0.4)),
    ],
)
def test_every_decision_has_reasons(decision_obj) -> None:
    assert decision_obj.reasons
