"""Power and sample-size helpers for controlled experiments."""

from __future__ import annotations

from math import ceil, sqrt

from scipy import stats


def binary_mde(
    baseline_rate: float,
    control_n: int,
    treatment_n: int,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
) -> float:
    """Minimum detectable absolute lift for a two-sided binary-metric test."""

    z_alpha = float(stats.norm.ppf(1 - alpha / 2))
    z_power = float(stats.norm.ppf(power))
    standard_error = sqrt(baseline_rate * (1 - baseline_rate) * (1 / control_n + 1 / treatment_n))
    return (z_alpha + z_power) * standard_error


def achieved_power_binary(
    baseline_rate: float,
    effect: float,
    control_n: int,
    treatment_n: int,
    *,
    alpha: float = 0.05,
) -> float:
    """Approximate achieved power for an observed absolute binary lift."""

    standard_error = sqrt(baseline_rate * (1 - baseline_rate) * (1 / control_n + 1 / treatment_n))
    if standard_error == 0:
        return 1.0
    z_alpha = float(stats.norm.ppf(1 - alpha / 2))
    non_centrality = abs(effect) / standard_error
    return float(stats.norm.sf(z_alpha - non_centrality))


def sample_size_per_arm_binary(
    baseline_rate: float,
    mde: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Balanced per-arm sample size needed for a binary metric MDE."""

    z_alpha = float(stats.norm.ppf(1 - alpha / 2))
    z_power = float(stats.norm.ppf(power))
    variance = 2 * baseline_rate * (1 - baseline_rate)
    return ceil(((z_alpha + z_power) ** 2 * variance) / (mde**2))
