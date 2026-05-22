"""Core statistics for online controlled experiments."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class EffectEstimate:
    metric: str
    control_mean: float
    treatment_mean: float
    effect: float
    standard_error: float
    ci_low: float
    ci_high: float
    p_value: float
    control_n: int
    treatment_n: int
    method: str
    relative_effect: float | None = None


@dataclass(frozen=True)
class SrmResult:
    counts: dict[str, int]
    expected: dict[str, float]
    chi_square: float
    p_value: float
    passed: bool


@dataclass(frozen=True)
class CupedResult:
    estimate: EffectEstimate
    theta: float
    covariate_mean: float
    variance_reduction: float


def _numeric_values(frame: pd.DataFrame, metric: str, variant: str) -> np.ndarray:
    values = frame.loc[frame["variant"] == variant, metric].dropna().astype(float).to_numpy()
    if values.size < 2:
        raise ValueError(f"Need at least two {variant} observations for {metric}")
    return values


def difference_in_means(
    frame: pd.DataFrame,
    metric: str,
    *,
    alpha: float = 0.05,
    method: str = "welch",
) -> EffectEstimate:
    """Estimate treatment minus control with a Welch standard error."""

    control = _numeric_values(frame, metric, "control")
    treatment = _numeric_values(frame, metric, "treatment")

    control_mean = float(control.mean())
    treatment_mean = float(treatment.mean())
    control_var = float(control.var(ddof=1))
    treatment_var = float(treatment.var(ddof=1))
    control_n = int(control.size)
    treatment_n = int(treatment.size)

    effect = treatment_mean - control_mean
    standard_error = sqrt((control_var / control_n) + (treatment_var / treatment_n))
    if standard_error == 0:
        p_value = 1.0 if effect == 0 else 0.0
        ci_low = ci_high = effect
    else:
        numerator = ((control_var / control_n) + (treatment_var / treatment_n)) ** 2
        denominator = ((control_var / control_n) ** 2 / (control_n - 1)) + (
            (treatment_var / treatment_n) ** 2 / (treatment_n - 1)
        )
        degrees_freedom = numerator / denominator if denominator else control_n + treatment_n - 2
        critical_value = float(stats.t.ppf(1 - alpha / 2, degrees_freedom))
        ci_low = effect - critical_value * standard_error
        ci_high = effect + critical_value * standard_error
        p_value = float(2 * stats.t.sf(abs(effect / standard_error), degrees_freedom))

    relative_effect = effect / control_mean if control_mean else None
    return EffectEstimate(
        metric=metric,
        control_mean=control_mean,
        treatment_mean=treatment_mean,
        effect=effect,
        standard_error=standard_error,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
        control_n=control_n,
        treatment_n=treatment_n,
        method=method,
        relative_effect=relative_effect,
    )


def cuped_adjusted_effect(
    frame: pd.DataFrame,
    metric: str,
    covariate: str,
    *,
    alpha: float = 0.05,
) -> CupedResult:
    """Apply CUPED using a pre-treatment covariate, then estimate the effect."""

    required = frame[["variant", metric, covariate]].dropna().copy()
    outcome = required[metric].astype(float).to_numpy()
    covariate_values = required[covariate].astype(float).to_numpy()
    covariate_variance = float(np.var(covariate_values, ddof=1))
    if covariate_variance == 0:
        theta = 0.0
    else:
        theta = float(np.cov(outcome, covariate_values, ddof=1)[0, 1] / covariate_variance)

    covariate_mean = float(covariate_values.mean())
    adjusted_metric = f"{metric}_cuped"
    required[adjusted_metric] = outcome - theta * (covariate_values - covariate_mean)
    adjusted_frame = required[["variant", adjusted_metric]].rename(
        columns={adjusted_metric: metric}
    )
    estimate = difference_in_means(adjusted_frame, metric, alpha=alpha, method=f"cuped:{covariate}")

    raw_variance = float(np.var(outcome, ddof=1))
    adjusted_variance = float(np.var(required[adjusted_metric].to_numpy(), ddof=1))
    variance_reduction = 0.0 if raw_variance == 0 else 1 - (adjusted_variance / raw_variance)
    return CupedResult(
        estimate=estimate,
        theta=theta,
        covariate_mean=covariate_mean,
        variance_reduction=variance_reduction,
    )


def sample_ratio_mismatch(
    frame: pd.DataFrame,
    *,
    expected_ratios: dict[str, float] | None = None,
    alpha: float = 0.001,
) -> SrmResult:
    """Run a chi-square sample-ratio mismatch check."""

    ratios = expected_ratios or {"control": 0.5, "treatment": 0.5}
    counts = {variant: int((frame["variant"] == variant).sum()) for variant in ratios}
    total = sum(counts.values())
    expected = {variant: total * ratio for variant, ratio in ratios.items()}
    chi_square = sum(
        ((counts[variant] - expected[variant]) ** 2) / expected[variant] for variant in ratios
    )
    p_value = float(stats.chi2.sf(chi_square, df=len(ratios) - 1))
    return SrmResult(
        counts=counts,
        expected=expected,
        chi_square=float(chi_square),
        p_value=p_value,
        passed=p_value >= alpha,
    )


def heterogeneous_effects(
    frame: pd.DataFrame,
    metric: str,
    segment: str,
    *,
    min_n_per_arm: int = 250,
) -> pd.DataFrame:
    """Estimate treatment effects by segment level, dropping thin slices."""

    rows: list[dict[str, object]] = []
    for level, level_frame in frame.groupby(segment, dropna=False):
        counts = level_frame["variant"].value_counts().to_dict()
        if min(counts.get("control", 0), counts.get("treatment", 0)) < min_n_per_arm:
            continue
        estimate = difference_in_means(level_frame, metric)
        rows.append(
            {
                "segment": segment,
                "level": str(level),
                "control_n": estimate.control_n,
                "treatment_n": estimate.treatment_n,
                "control_mean": estimate.control_mean,
                "treatment_mean": estimate.treatment_mean,
                "effect": estimate.effect,
                "ci_low": estimate.ci_low,
                "ci_high": estimate.ci_high,
                "p_value": estimate.p_value,
            }
        )
    return pd.DataFrame(rows).sort_values("effect", ascending=False).reset_index(drop=True)
