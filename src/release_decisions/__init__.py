"""Responsible release-gate engine.

Turns commercial evidence and customer-outcome guardrails into an explainable
release decision: ship / limited_rollout / experiment_only / needs_human_review /
block.
"""

from src.release_decisions.decision_engine import (
    GateCheck,
    ReleaseDecision,
    ReleaseSignals,
    decide,
)
from src.release_decisions.thresholds import ReleaseThresholds

__all__ = [
    "GateCheck",
    "ReleaseDecision",
    "ReleaseSignals",
    "ReleaseThresholds",
    "decide",
]
