"""Explainable release-gate decision engine.

The engine separates two questions a responsible fintech must answer together:

1. Is the commercial **evidence** strong enough to act? (evidence tier)
2. Do customer-outcome **guardrails** raise any concern? (gate checks)

It then maps the pair to a single decision with ordered, human-readable reasons.
Customer-outcome concerns always dominate commercial evidence: a strong uplift never
overrides a block-level harm signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.release_decisions.thresholds import DEFAULT_THRESHOLDS, ReleaseThresholds

Status = Literal["pass", "warn", "review", "block"]
Decision = Literal[
    "ship",
    "limited_rollout",
    "experiment_only",
    "needs_human_review",
    "block",
]
EvidenceTier = Literal["ship", "rollout", "insufficient"]

_SEVERITY: dict[Status, int] = {"pass": 0, "warn": 1, "review": 2, "block": 3}


@dataclass(frozen=True)
class ReleaseSignals:
    """Inputs describing a proposed product / pricing / onboarding / referral change."""

    feature_name: str
    # Commercial evidence.
    business_uplift: float  # estimated effect (fraction, e.g. 0.031 == 3.1pp)
    evidence_strength: float  # 0..1 confidence the effect is real and stable
    incrementality_confirmed: bool = True  # causal evidence supports incrementality
    experiment_valid: bool = True  # SRM passed, no validity flags
    # Customer-outcome guardrails (deltas vs control; higher = worse).
    complaint_rate_delta: float = 0.0
    support_burden_delta: float = 0.0
    fairness_gap: float = 0.0  # worst-vs-best segment outcome gap, 0..1
    vulnerable_customer_impact: float = 0.0  # signed; negative = harm
    fair_value_score: float = 1.0  # 0..1, higher = fairer
    # Model / data operations.
    model_calibration_error: float = 0.0
    model_drift_psi: float = 0.0
    data_quality_ok: bool = True
    human_review_load: float = 0.0  # 0..1 review-capacity utilisation


@dataclass(frozen=True)
class GateCheck:
    name: str
    status: Status
    detail: str


@dataclass(frozen=True)
class ReleaseDecision:
    feature_name: str
    decision: Decision
    evidence_tier: EvidenceTier
    checks: list[GateCheck] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def is_actionable(self) -> bool:
        """True when the change can move toward customers without human escalation."""
        return self.decision in {"ship", "limited_rollout"}


def _upper_bound_check(
    name: str,
    value: float,
    *,
    warn: float,
    block: float,
    label: str,
) -> GateCheck:
    """Check for a metric where higher is worse (complaints, drift, ...)."""
    if value >= block:
        status: Status = "block"
    elif value >= warn:
        status = "warn"
    else:
        status = "pass"
    return GateCheck(name, status, f"{label}: {value:.4g} (warn>={warn:.4g}, block>={block:.4g})")


def _guardrail_checks(signals: ReleaseSignals, t: ReleaseThresholds) -> list[GateCheck]:
    checks = [
        _upper_bound_check(
            "complaint_risk",
            signals.complaint_rate_delta,
            warn=t.warn_complaint_delta,
            block=t.block_complaint_delta,
            label="complaint-rate delta",
        ),
        _upper_bound_check(
            "support_burden",
            signals.support_burden_delta,
            warn=t.warn_support_delta,
            block=t.block_support_delta,
            label="support-burden delta",
        ),
        _upper_bound_check(
            "fairness_gap",
            signals.fairness_gap,
            warn=t.warn_fairness_gap,
            block=t.block_fairness_gap,
            label="worst-segment outcome gap",
        ),
        _upper_bound_check(
            "model_calibration",
            signals.model_calibration_error,
            warn=t.warn_calibration_error,
            block=t.block_calibration_error,
            label="calibration error",
        ),
        _upper_bound_check(
            "model_drift",
            signals.model_drift_psi,
            warn=t.warn_drift_psi,
            block=t.block_drift_psi,
            label="drift PSI",
        ),
    ]

    # Vulnerable-customer impact (signed; negative = harm).
    impact = signals.vulnerable_customer_impact
    if impact <= t.block_vulnerable_impact:
        vuln_status: Status = "block"
    elif impact <= t.review_vulnerable_impact:
        vuln_status = "review"
    else:
        vuln_status = "pass"
    checks.append(
        GateCheck(
            "vulnerable_customer_impact",
            vuln_status,
            f"vulnerable-customer impact: {impact:+.4g} "
            f"(review<={t.review_vulnerable_impact:+.4g}, block<={t.block_vulnerable_impact:+.4g})",
        )
    )

    # Fair-value score (higher = fairer).
    fv = signals.fair_value_score
    if fv < t.review_fair_value_score:
        fv_status: Status = "review"
    elif fv < t.warn_fair_value_score:
        fv_status = "warn"
    else:
        fv_status = "pass"
    checks.append(
        GateCheck(
            "fair_value",
            fv_status,
            f"fair-value score: {fv:.4g} "
            f"(warn<{t.warn_fair_value_score:.4g}, review<{t.review_fair_value_score:.4g})",
        )
    )

    # Operational gates.
    checks.append(
        GateCheck(
            "data_quality",
            "pass" if signals.data_quality_ok else "block",
            "data quality OK" if signals.data_quality_ok else "data-quality check failed",
        )
    )
    review_load_status: Status = (
        "review" if signals.human_review_load >= t.review_human_review_load else "pass"
    )
    checks.append(
        GateCheck(
            "human_review_load",
            review_load_status,
            f"human-review load: {signals.human_review_load:.4g} "
            f"(review>={t.review_human_review_load:.4g})",
        )
    )
    return checks


def _evidence_tier(signals: ReleaseSignals, t: ReleaseThresholds) -> EvidenceTier:
    if (
        not signals.experiment_valid
        or not signals.incrementality_confirmed
        or signals.business_uplift <= t.min_business_uplift
        or signals.evidence_strength < t.rollout_evidence_strength
    ):
        return "insufficient"
    if signals.evidence_strength >= t.ship_evidence_strength:
        return "ship"
    return "rollout"


def _worst_status(checks: list[GateCheck]) -> Status:
    return max(checks, key=lambda c: _SEVERITY[c.status]).status if checks else "pass"


def _evidence_reason(signals: ReleaseSignals, tier: EvidenceTier) -> str:
    if not signals.experiment_valid:
        return "Experiment validity failed (e.g. sample-ratio mismatch)."
    if not signals.incrementality_confirmed:
        return "Incrementality not confirmed by causal evidence."
    if tier == "insufficient":
        return (
            f"Evidence insufficient for rollout (uplift={signals.business_uplift:+.4g}, "
            f"strength={signals.evidence_strength:.2f})."
        )
    return (
        f"Evidence {tier}-grade (uplift={signals.business_uplift:+.4g}, "
        f"strength={signals.evidence_strength:.2f})."
    )


def decide(
    signals: ReleaseSignals,
    thresholds: ReleaseThresholds = DEFAULT_THRESHOLDS,
) -> ReleaseDecision:
    """Combine evidence tier and guardrail checks into an explainable decision."""

    checks = _guardrail_checks(signals, thresholds)
    tier = _evidence_tier(signals, thresholds)
    worst = _SEVERITY[_worst_status(checks)]

    if worst == _SEVERITY["block"]:
        decision: Decision = "block"
    elif worst == _SEVERITY["review"]:
        decision = "needs_human_review"
    elif tier == "insufficient":
        decision = "experiment_only"
    elif tier == "ship" and worst < _SEVERITY["warn"]:
        decision = "ship"
    else:
        decision = "limited_rollout"

    reasons = _build_reasons(decision, checks, tier, signals)
    return ReleaseDecision(
        feature_name=signals.feature_name,
        decision=decision,
        evidence_tier=tier,
        checks=checks,
        reasons=reasons,
    )


def _build_reasons(
    decision: Decision,
    checks: list[GateCheck],
    tier: EvidenceTier,
    signals: ReleaseSignals,
) -> list[str]:
    blocking = [c.detail for c in checks if c.status == "block"]
    review = [c.detail for c in checks if c.status == "review"]
    warnings = [c.detail for c in checks if c.status == "warn"]
    evidence = _evidence_reason(signals, tier)

    if decision == "block":
        return ["Blocked by customer-outcome / data guardrails:", *blocking, evidence]
    if decision == "needs_human_review":
        return ["Escalated for human review:", *review, *warnings, evidence]
    if decision == "experiment_only":
        return [evidence, "Keep as an experiment until evidence is strong enough."]
    if decision == "limited_rollout":
        caveats = warnings or ["evidence supports a capped rollout rather than full ship"]
        return [evidence, "Proceed with a limited rollout. Caveats:", *caveats]
    return [evidence, "Strong evidence and no material customer-outcome concern."]
