"""Score the fair value of an offer and derive a fairness-aware governance action.

The commercial pricing mart already recommends an action (scale / test / hold / ...).
This module computes a transparent ``fair_value_score`` from observed customer-outcome
guardrails and can **downgrade** a commercially attractive offer: a "scale"
recommendation with a poor fair-value score becomes "hold_fair_value" or
"human_review". The thesis from the release-gate engine applied to pricing -- customer
fairness can override commercial appeal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

GovernanceAction = Literal["scale", "monitor", "hold_fair_value", "human_review"]


@dataclass(frozen=True)
class FairValueThresholds:
    # Reference levels used to normalise each guardrail into a 0..1 penalty.
    complaint_ref: float = 0.025
    support_ref: float = 0.20
    review_ref: float = 0.25
    # Penalty weights (sum to 1.0).
    complaint_weight: float = 0.40
    support_weight: float = 0.30
    review_weight: float = 0.30
    # Block-level guardrails force human review regardless of score.
    block_complaint: float = 0.025
    block_support: float = 0.30
    block_review: float = 0.40
    # Fair-value score gates.
    min_fair_value_score: float = 0.60  # below this an offer is held
    scale_fair_value_score: float = 0.75  # at/above this a "scale" offer may scale


DEFAULT_FAIR_VALUE_THRESHOLDS = FairValueThresholds()


@dataclass(frozen=True)
class FairValueAssessment:
    offer_id: str
    fair_value_score: float
    mart_recommended_action: str
    governance_action: GovernanceAction
    reason: str


def fair_value_score(
    *,
    complaint_rate_14d: float,
    support_contact_rate_14d: float,
    human_review_rate: float,
    thresholds: FairValueThresholds = DEFAULT_FAIR_VALUE_THRESHOLDS,
) -> float:
    """Return a 0..1 fair-value score (higher = fairer) from outcome guardrails."""

    t = thresholds
    penalty = (
        t.complaint_weight * min(complaint_rate_14d / t.complaint_ref, 1.0)
        + t.support_weight * min(support_contact_rate_14d / t.support_ref, 1.0)
        + t.review_weight * min(human_review_rate / t.review_ref, 1.0)
    )
    return round(max(0.0, min(1.0, 1.0 - penalty)), 4)


def _governance_action(
    *,
    score: float,
    mart_recommended_action: str,
    complaint_rate_14d: float,
    support_contact_rate_14d: float,
    human_review_rate: float,
    thresholds: FairValueThresholds,
) -> tuple[GovernanceAction, str]:
    t = thresholds
    if (
        complaint_rate_14d >= t.block_complaint
        or support_contact_rate_14d >= t.block_support
        or human_review_rate >= t.block_review
    ):
        return "human_review", "Block-level customer-outcome guardrail breached."
    if score < t.min_fair_value_score:
        suffix = " (downgraded from scale)" if mart_recommended_action == "scale" else ""
        reason = f"Fair-value score below {t.min_fair_value_score:.2f}{suffix}."
        return "hold_fair_value", reason
    if mart_recommended_action == "scale" and score >= t.scale_fair_value_score:
        return "scale", "Strong fair value and a positive commercial recommendation."
    return "monitor", "Acceptable fair value; monitor before scaling."


def assess_offer(
    *,
    offer_id: str,
    complaint_rate_14d: float,
    support_contact_rate_14d: float,
    human_review_rate: float,
    mart_recommended_action: str,
    thresholds: FairValueThresholds = DEFAULT_FAIR_VALUE_THRESHOLDS,
) -> FairValueAssessment:
    score = fair_value_score(
        complaint_rate_14d=complaint_rate_14d,
        support_contact_rate_14d=support_contact_rate_14d,
        human_review_rate=human_review_rate,
        thresholds=thresholds,
    )
    action, reason = _governance_action(
        score=score,
        mart_recommended_action=mart_recommended_action,
        complaint_rate_14d=complaint_rate_14d,
        support_contact_rate_14d=support_contact_rate_14d,
        human_review_rate=human_review_rate,
        thresholds=thresholds,
    )
    return FairValueAssessment(
        offer_id=offer_id,
        fair_value_score=score,
        mart_recommended_action=mart_recommended_action,
        governance_action=action,
        reason=reason,
    )


def assess_offers(
    offers: pd.DataFrame,
    *,
    thresholds: FairValueThresholds = DEFAULT_FAIR_VALUE_THRESHOLDS,
) -> pd.DataFrame:
    """Assess a pricing-recommendation-style frame, one row per offer.

    Expected columns: ``offer_id``, ``complaint_rate_14d``,
    ``support_contact_rate_14d``, ``human_review_rate``, ``recommended_action``.
    Returns the input columns plus ``fair_value_score``, ``governance_action``,
    ``reason``, and ``downgraded`` (True when fairness overrode a "scale").
    """

    columns = [
        "offer_id",
        "fair_value_score",
        "recommended_action",
        "governance_action",
        "downgraded",
        "reason",
    ]
    if offers.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    for record in offers.to_dict(orient="records"):
        assessment = assess_offer(
            offer_id=str(record["offer_id"]),
            complaint_rate_14d=float(record["complaint_rate_14d"]),
            support_contact_rate_14d=float(record["support_contact_rate_14d"]),
            human_review_rate=float(record["human_review_rate"]),
            mart_recommended_action=str(record["recommended_action"]),
            thresholds=thresholds,
        )
        rows.append(
            {
                "offer_id": assessment.offer_id,
                "fair_value_score": assessment.fair_value_score,
                "recommended_action": assessment.mart_recommended_action,
                "governance_action": assessment.governance_action,
                "downgraded": (
                    assessment.mart_recommended_action == "scale"
                    and assessment.governance_action != "scale"
                ),
                "reason": assessment.reason,
            }
        )
    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values("fair_value_score")
        .reset_index(drop=True)
    )
