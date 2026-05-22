"""Difference-in-differences helpers for regional experiments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


@dataclass(frozen=True)
class DidResult:
    metric: str
    effect_per_region_day: float
    standard_error: float
    ci_low: float
    ci_high: float
    p_value: float
    pre_treated_mean: float
    post_treated_mean: float
    pre_control_mean: float
    post_control_mean: float


def estimate_did(
    frame: pd.DataFrame,
    metric: str,
    *,
    treatment_column: str = "treated_region",
    post_column: str = "post_period",
    cluster_column: str = "region",
) -> DidResult:
    """Estimate a two-way fixed-effect DiD with region and date fixed effects."""

    panel = frame.copy()
    panel["treated_int"] = panel[treatment_column].astype(int)
    panel["post_int"] = panel[post_column].astype(int)
    panel["did"] = panel["treated_int"] * panel["post_int"]
    model = smf.ols(f"{metric} ~ did + C(region) + C(date_day)", data=panel).fit(
        cov_type="cluster",
        cov_kwds={"groups": panel[cluster_column]},
    )
    effect = float(model.params["did"])
    standard_error = float(model.bse["did"])
    ci_low, ci_high = model.conf_int().loc["did"].astype(float)

    grouped = panel.groupby(["treated_int", "post_int"])[metric].mean()
    return DidResult(
        metric=metric,
        effect_per_region_day=effect,
        standard_error=standard_error,
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        p_value=float(model.pvalues["did"]),
        pre_treated_mean=float(grouped.loc[(1, 0)]),
        post_treated_mean=float(grouped.loc[(1, 1)]),
        pre_control_mean=float(grouped.loc[(0, 0)]),
        post_control_mean=float(grouped.loc[(0, 1)]),
    )


def parallel_trends_gap(
    frame: pd.DataFrame,
    metric: str,
    *,
    treatment_column: str = "treated_region",
    post_column: str = "post_period",
) -> float:
    """Compare treated versus control daily slopes before treatment."""

    pre = frame.loc[~frame[post_column]].copy()
    first_day = pd.to_datetime(pre["date_day"]).min()
    pre["day_index"] = (pd.to_datetime(pre["date_day"]) - first_day).dt.days
    slopes = []
    for treated, group in pre.groupby(treatment_column):
        slope = np.polyfit(group["day_index"], group[metric], deg=1)[0]
        slopes.append((bool(treated), float(slope)))
    slope_map = dict(slopes)
    return slope_map.get(True, 0.0) - slope_map.get(False, 0.0)


def placebo_did_by_region(
    frame: pd.DataFrame,
    metric: str,
    *,
    treatment_column: str = "treated_region",
) -> pd.DataFrame:
    """Assign each donor region as placebo treated and estimate its post-period DiD."""

    donor_regions = sorted(frame.loc[~frame[treatment_column], "region"].unique())
    rows: list[dict[str, float | str]] = []
    for region in donor_regions:
        placebo = frame.copy()
        placebo["placebo_treated"] = placebo["region"] == region
        result = estimate_did(
            placebo,
            metric,
            treatment_column="placebo_treated",
            post_column="post_period",
        )
        rows.append(
            {
                "region": region,
                "effect_per_region_day": result.effect_per_region_day,
                "p_value": result.p_value,
            }
        )
    return pd.DataFrame(rows).sort_values("effect_per_region_day", ascending=False)
