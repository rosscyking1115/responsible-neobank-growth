"""Synthetic-control helpers for geo incrementality analysis."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass(frozen=True)
class SyntheticControlResult:
    metric: str
    treated_regions: list[str]
    donor_weights: pd.DataFrame
    post_effect_total: float
    post_effect_per_day: float
    pre_rmse: float
    post_actual_total: float
    post_synthetic_total: float


def _fit_simplex_weights(treated_pre: np.ndarray, donor_pre: np.ndarray) -> np.ndarray:
    donors = donor_pre.shape[1]
    initial = np.full(donors, 1 / donors)
    constraints = {"type": "eq", "fun": lambda weights: np.sum(weights) - 1}
    bounds = [(0.0, 1.0)] * donors

    def objective(weights: np.ndarray) -> float:
        residual = treated_pre - donor_pre @ weights
        return float(np.mean(residual**2))

    result = minimize(objective, initial, bounds=bounds, constraints=constraints, method="SLSQP")
    if not result.success:
        return initial
    return np.asarray(result.x, dtype=float)


def estimate_synthetic_control(
    frame: pd.DataFrame,
    metric: str,
    *,
    treatment_column: str = "treated_region",
    post_column: str = "post_period",
) -> SyntheticControlResult:
    """Fit donor-region weights to the pre-period treated aggregate."""

    panel = frame.copy()
    treated_regions = sorted(panel.loc[panel[treatment_column], "region"].unique())
    donor_regions = sorted(panel.loc[~panel[treatment_column], "region"].unique())
    daily = panel.pivot_table(index="date_day", columns="region", values=metric, aggfunc="sum")
    treated_series = daily[treated_regions].sum(axis=1)
    donor_matrix = daily[donor_regions]
    post_mask = (
        panel[["date_day", post_column]]
        .drop_duplicates()
        .set_index("date_day")
        .loc[daily.index, post_column]
        .astype(bool)
        .to_numpy()
    )

    treated_pre = treated_series.loc[~post_mask].to_numpy(dtype=float)
    donor_pre = donor_matrix.loc[~post_mask].to_numpy(dtype=float)
    weights = _fit_simplex_weights(treated_pre, donor_pre)
    synthetic = donor_matrix.to_numpy(dtype=float) @ weights
    actual = treated_series.to_numpy(dtype=float)
    effects = actual - synthetic
    pre_rmse = float(np.sqrt(np.mean(effects[~post_mask] ** 2)))
    post_effect_total = float(effects[post_mask].sum())
    post_days = int(post_mask.sum())
    weights_frame = pd.DataFrame({"region": donor_regions, "weight": weights}).sort_values(
        "weight",
        ascending=False,
    )
    return SyntheticControlResult(
        metric=metric,
        treated_regions=treated_regions,
        donor_weights=weights_frame,
        post_effect_total=post_effect_total,
        post_effect_per_day=post_effect_total / post_days,
        pre_rmse=pre_rmse,
        post_actual_total=float(actual[post_mask].sum()),
        post_synthetic_total=float(synthetic[post_mask].sum()),
    )


def synthetic_control_placebos(
    frame: pd.DataFrame,
    metric: str,
    *,
    treatment_column: str = "treated_region",
) -> pd.DataFrame:
    """Run synthetic control with each donor region as a placebo treated region."""

    donor_regions = sorted(frame.loc[~frame[treatment_column], "region"].unique())
    rows: list[dict[str, float | str]] = []
    for region in donor_regions:
        placebo = frame.copy()
        placebo["placebo_treated"] = placebo["region"] == region
        result = estimate_synthetic_control(
            placebo,
            metric,
            treatment_column="placebo_treated",
            post_column="post_period",
        )
        rows.append(
            {
                "region": region,
                "post_effect_total": result.post_effect_total,
                "post_effect_per_day": result.post_effect_per_day,
                "pre_rmse": result.pre_rmse,
            }
        )
    return pd.DataFrame(rows).sort_values("post_effect_total", ascending=False)
