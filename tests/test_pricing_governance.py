from __future__ import annotations

import pandas as pd
import pytest

from src.pricing_governance import (
    FairValueThresholds,
    assess_offer,
    assess_offers,
    fair_value_score,
)


def test_clean_offer_scores_one() -> None:
    score = fair_value_score(
        complaint_rate_14d=0.0,
        support_contact_rate_14d=0.0,
        human_review_rate=0.0,
    )
    assert score == 1.0


def test_complaint_at_reference_applies_full_complaint_weight() -> None:
    score = fair_value_score(
        complaint_rate_14d=0.025,  # == complaint_ref -> full complaint penalty (0.40)
        support_contact_rate_14d=0.0,
        human_review_rate=0.0,
    )
    assert score == pytest.approx(0.60)


def test_worst_case_scores_zero() -> None:
    score = fair_value_score(
        complaint_rate_14d=1.0,
        support_contact_rate_14d=1.0,
        human_review_rate=1.0,
    )
    assert score == 0.0


def test_clean_scale_offer_scales() -> None:
    assessment = assess_offer(
        offer_id="savings_boost",
        complaint_rate_14d=0.0,
        support_contact_rate_14d=0.0,
        human_review_rate=0.0,
        mart_recommended_action="scale",
    )
    assert assessment.governance_action == "scale"


def test_poor_fair_value_downgrades_scale_to_hold() -> None:
    assessment = assess_offer(
        offer_id="teaser_bundle",
        complaint_rate_14d=0.02,
        support_contact_rate_14d=0.15,
        human_review_rate=0.20,
        mart_recommended_action="scale",
    )
    assert assessment.fair_value_score < 0.60
    assert assessment.governance_action == "hold_fair_value"


def test_block_level_complaint_forces_human_review() -> None:
    assessment = assess_offer(
        offer_id="risky_offer",
        complaint_rate_14d=0.03,  # >= block_complaint
        support_contact_rate_14d=0.0,
        human_review_rate=0.0,
        mart_recommended_action="scale",
    )
    assert assessment.governance_action == "human_review"


def test_thresholds_are_configurable() -> None:
    strict = FairValueThresholds(scale_fair_value_score=0.99)
    assessment = assess_offer(
        offer_id="savings_boost",
        complaint_rate_14d=0.002,
        support_contact_rate_14d=0.0,
        human_review_rate=0.0,
        mart_recommended_action="scale",
        thresholds=strict,
    )
    # Fair value just under the strict scale gate -> monitor instead of scale.
    assert assessment.governance_action == "monitor"


def test_assess_offers_flags_downgrades() -> None:
    offers = pd.DataFrame(
        {
            "offer_id": ["clean_scale", "unfair_scale"],
            "complaint_rate_14d": [0.0, 0.02],
            "support_contact_rate_14d": [0.0, 0.15],
            "human_review_rate": [0.0, 0.20],
            "recommended_action": ["scale", "scale"],
        }
    )
    result = assess_offers(offers)
    by_offer = result.set_index("offer_id")
    assert by_offer.loc["clean_scale", "governance_action"] == "scale"
    assert not by_offer.loc["clean_scale", "downgraded"]
    assert by_offer.loc["unfair_scale", "governance_action"] == "hold_fair_value"
    assert by_offer.loc["unfair_scale", "downgraded"]


def test_assess_offers_empty_frame() -> None:
    result = assess_offers(pd.DataFrame())
    assert result.empty
    assert "governance_action" in result.columns


def test_offer_fair_value_aggregates_recommendation_mart() -> None:
    from app.dashboard_data import offer_fair_value

    recommendations = pd.DataFrame(
        {
            "offer_id": ["clean", "clean", "risky"],
            "exposures": [100, 100, 50],
            "complaint_rate_14d": [0.0, 0.0, 0.03],
            "support_contact_rate_14d": [0.0, 0.0, 0.0],
            "human_review_rate": [0.0, 0.0, 0.0],
            "recommended_action": ["scale", "scale", "scale"],
        }
    )
    result = offer_fair_value(recommendations).set_index("offer_id")
    assert result.loc["clean", "governance_action"] == "scale"
    assert result.loc["risky", "governance_action"] == "human_review"
    assert int(result.loc["clean", "exposures"]) == 200
