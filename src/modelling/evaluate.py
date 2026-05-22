"""Model calibration, thresholding, and business-impact evaluation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from src.modelling.features import TARGET_COLUMN


@dataclass(frozen=True)
class ModelMetrics:
    roc_auc: float
    average_precision: float
    brier_score: float
    log_loss: float
    expected_calibration_error: float
    activation_rate: float
    rows: int


@dataclass(frozen=True)
class ThresholdResult:
    threshold: float
    targeted_users: int
    targeting_rate: float
    expected_incremental_activations: float
    expected_net_value_gbp: float
    vulnerable_targeting_rate: float
    non_vulnerable_targeting_rate: float


@dataclass(frozen=True)
class GuardrailCheck:
    name: str
    value: float
    limit: float
    passed: bool
    direction: str


def expected_calibration_error(
    y_true: pd.Series | np.ndarray,
    probabilities: np.ndarray,
    *,
    bins: int = 10,
) -> float:
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(probabilities, dtype=float)
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        mask = (predicted >= lower) & (predicted < upper if upper < 1 else predicted <= upper)
        if not mask.any():
            continue
        weight = mask.mean()
        ece += weight * abs(actual[mask].mean() - predicted[mask].mean())
    return float(ece)


def classification_metrics(y_true: pd.Series, probabilities: np.ndarray) -> ModelMetrics:
    return ModelMetrics(
        roc_auc=float(roc_auc_score(y_true, probabilities)),
        average_precision=float(average_precision_score(y_true, probabilities)),
        brier_score=float(brier_score_loss(y_true, probabilities)),
        log_loss=float(log_loss(y_true, np.clip(probabilities, 1e-6, 1 - 1e-6))),
        expected_calibration_error=expected_calibration_error(y_true, probabilities),
        activation_rate=float(pd.Series(y_true).mean()),
        rows=int(len(y_true)),
    )


def intervention_lift_curve(probabilities: np.ndarray) -> np.ndarray:
    """Assumed activation uplift for a helpful onboarding nudge by baseline propensity."""

    risk = 1 - np.asarray(probabilities, dtype=float)
    return np.clip(0.01 + 0.055 * risk, 0.01, 0.08)


def threshold_sweep(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    *,
    value_per_activation_gbp: float,
    contact_cost_gbp: float = 0.45,
    thresholds: np.ndarray | None = None,
) -> pd.DataFrame:
    """Score targeting users at or below each activation-propensity threshold."""

    threshold_values = thresholds if thresholds is not None else np.arange(0.20, 0.81, 0.05)
    rows: list[dict[str, float | int]] = []
    lifts = intervention_lift_curve(probabilities)
    vulnerable = frame["vulnerable_customer_flag"].astype(bool).to_numpy()
    for threshold in threshold_values:
        target = probabilities <= threshold
        targeted_users = int(target.sum())
        if targeted_users == 0:
            continue
        incremental_activations = float(lifts[target].sum())
        net_value = (
            incremental_activations * value_per_activation_gbp
            - targeted_users * contact_cost_gbp
        )
        vulnerable_rate = float(target[vulnerable].mean()) if vulnerable.any() else 0.0
        non_vulnerable_rate = float(target[~vulnerable].mean()) if (~vulnerable).any() else 0.0
        rows.append(
            {
                "threshold": float(threshold),
                "targeted_users": targeted_users,
                "targeting_rate": float(target.mean()),
                "expected_incremental_activations": incremental_activations,
                "expected_net_value_gbp": float(net_value),
                "vulnerable_targeting_rate": vulnerable_rate,
                "non_vulnerable_targeting_rate": non_vulnerable_rate,
            }
        )
    return pd.DataFrame(rows)


def choose_threshold(thresholds: pd.DataFrame) -> ThresholdResult:
    best = thresholds.sort_values(
        ["expected_net_value_gbp", "expected_incremental_activations"],
        ascending=False,
    ).iloc[0]
    return ThresholdResult(
        threshold=float(best.threshold),
        targeted_users=int(best.targeted_users),
        targeting_rate=float(best.targeting_rate),
        expected_incremental_activations=float(best.expected_incremental_activations),
        expected_net_value_gbp=float(best.expected_net_value_gbp),
        vulnerable_targeting_rate=float(best.vulnerable_targeting_rate),
        non_vulnerable_targeting_rate=float(best.non_vulnerable_targeting_rate),
    )


def customer_outcome_guardrails(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    threshold: float,
    *,
    max_vulnerable_targeting_ratio: float = 2.50,
    max_vulnerable_false_negative_gap: float = 0.08,
    max_low_income_false_negative_gap: float = 0.08,
) -> list[GuardrailCheck]:
    """Consumer Duty-style checks for disproportionate targeting or missed support."""

    target = probabilities <= threshold
    vulnerable = frame["vulnerable_customer_flag"].astype(bool).to_numpy()
    activated = frame[TARGET_COLUMN].astype(bool).to_numpy()
    low_income = frame["income_segment"].isin(["student", "low"]).to_numpy()

    vulnerable_rate = float(target[vulnerable].mean()) if vulnerable.any() else 0.0
    non_vulnerable_rate = float(target[~vulnerable].mean()) if (~vulnerable).any() else 0.0
    vulnerable_ratio = vulnerable_rate / max(non_vulnerable_rate, 1e-6)

    false_negative = (~target) & (~activated)
    vulnerable_fn = float(false_negative[vulnerable].mean()) if vulnerable.any() else 0.0
    non_vulnerable_fn = float(false_negative[~vulnerable].mean()) if (~vulnerable).any() else 0.0
    low_income_fn = float(false_negative[low_income].mean()) if low_income.any() else 0.0
    other_income_fn = float(false_negative[~low_income].mean()) if (~low_income).any() else 0.0

    return [
        GuardrailCheck(
            name="vulnerable_targeting_ratio",
            value=vulnerable_ratio,
            limit=max_vulnerable_targeting_ratio,
            passed=vulnerable_ratio <= max_vulnerable_targeting_ratio,
            direction="<=",
        ),
        GuardrailCheck(
            name="vulnerable_false_negative_gap",
            value=vulnerable_fn - non_vulnerable_fn,
            limit=max_vulnerable_false_negative_gap,
            passed=(vulnerable_fn - non_vulnerable_fn) <= max_vulnerable_false_negative_gap,
            direction="<=",
        ),
        GuardrailCheck(
            name="low_income_false_negative_gap",
            value=low_income_fn - other_income_fn,
            limit=max_low_income_false_negative_gap,
            passed=(low_income_fn - other_income_fn) <= max_low_income_false_negative_gap,
            direction="<=",
        ),
    ]
