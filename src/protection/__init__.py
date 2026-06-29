"""Customer-protection / scam-intervention simulation.

A scoped, responsible-intervention simulation: it maps risk signals on a transfer to
a *supportive* response (education, soft friction, cooling-off, human review). It is
NOT a fraud detector and never blocks a payment.
"""

from src.protection.friction_rules import DEFAULT_PROTECTION_THRESHOLDS, ProtectionThresholds
from src.protection.scam_intervention_sim import (
    SUPPORTIVE_ACTIONS,
    InterventionDecision,
    ProtectionEvent,
    assess_events,
    decide_intervention,
    risk_score,
)

__all__ = [
    "DEFAULT_PROTECTION_THRESHOLDS",
    "SUPPORTIVE_ACTIONS",
    "InterventionDecision",
    "ProtectionEvent",
    "ProtectionThresholds",
    "assess_events",
    "decide_intervention",
    "risk_score",
]
