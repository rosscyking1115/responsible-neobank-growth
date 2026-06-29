"""Fair-value pricing governance.

Adds a fairness lens on top of the commercial pricing recommendation: an offer that
looks attractive on margin can still be held or sent to human review if its observed
customer-outcome guardrails (complaints, support burden, human-review load) point to
poor customer value.
"""

from src.pricing_governance.fair_value import (
    FairValueAssessment,
    FairValueThresholds,
    assess_offer,
    assess_offers,
    fair_value_score,
)

__all__ = [
    "FairValueAssessment",
    "FairValueThresholds",
    "assess_offer",
    "assess_offers",
    "fair_value_score",
]
