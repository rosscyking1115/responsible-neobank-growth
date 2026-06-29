"""Configurable thresholds for the release-gate engine.

Defaults are deliberately conservative: a release ships only with strong evidence
and no material customer-outcome concern. All percentage-point fields are expressed
as fractions (0.01 == 1 percentage point).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReleaseThresholds:
    # --- evidence (commercial) ---
    min_business_uplift: float = 0.0  # uplift must be positive to roll out at all
    ship_evidence_strength: float = 0.80  # >= this is ship-grade evidence
    rollout_evidence_strength: float = 0.60  # >= this supports a limited rollout

    # --- customer-outcome guardrails (higher = worse) ---
    warn_complaint_delta: float = 0.003
    block_complaint_delta: float = 0.010
    warn_support_delta: float = 0.010
    block_support_delta: float = 0.030
    warn_fairness_gap: float = 0.05
    block_fairness_gap: float = 0.10

    # vulnerable-customer impact is signed; negative = harm.
    review_vulnerable_impact: float = -0.010
    block_vulnerable_impact: float = -0.030

    # fair-value score (higher = fairer).
    warn_fair_value_score: float = 0.50
    review_fair_value_score: float = 0.30

    # --- model / data operations ---
    warn_calibration_error: float = 0.08
    block_calibration_error: float = 0.15
    warn_drift_psi: float = 0.10
    block_drift_psi: float = 0.25
    review_human_review_load: float = 0.85


DEFAULT_THRESHOLDS = ReleaseThresholds()
