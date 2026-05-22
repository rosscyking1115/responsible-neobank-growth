"""Customer-outcome and operational guardrail helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.experiments.analysis import EffectEstimate, difference_in_means


@dataclass(frozen=True)
class GuardrailSpec:
    metric: str
    label: str
    max_allowed_increase: float | None = None
    min_allowed_effect: float | None = None


@dataclass(frozen=True)
class GuardrailResult:
    spec: GuardrailSpec
    estimate: EffectEstimate
    passed: bool
    reason: str


def evaluate_guardrail(frame: pd.DataFrame, spec: GuardrailSpec) -> GuardrailResult:
    """Evaluate a guardrail using the confidence interval, not just the point estimate."""

    estimate = difference_in_means(frame, spec.metric)
    passed = True
    reasons: list[str] = []
    if spec.max_allowed_increase is not None:
        increase_passed = estimate.ci_high <= spec.max_allowed_increase
        passed = passed and increase_passed
        reasons.append(f"upper CI <= {spec.max_allowed_increase:.4f}")
    if spec.min_allowed_effect is not None:
        lower_passed = estimate.ci_low >= spec.min_allowed_effect
        passed = passed and lower_passed
        reasons.append(f"lower CI >= {spec.min_allowed_effect:.4f}")
    return GuardrailResult(
        spec=spec,
        estimate=estimate,
        passed=passed,
        reason=", ".join(reasons),
    )


def evaluate_guardrails(
    frame: pd.DataFrame,
    specs: list[GuardrailSpec],
) -> list[GuardrailResult]:
    return [evaluate_guardrail(frame, spec) for spec in specs]
