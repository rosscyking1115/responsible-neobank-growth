from __future__ import annotations

import numpy as np
import pandas as pd

from src.experiments.did import estimate_did, parallel_trends_gap, placebo_did_by_region
from src.experiments.run_referral_incrementality import (
    analyse_referral_incrementality,
    render_markdown,
)
from src.experiments.synthetic_control import (
    estimate_synthetic_control,
    synthetic_control_placebos,
)


def _geo_panel() -> pd.DataFrame:
    rng = np.random.default_rng(21)
    regions = ["North West", "Wales", "London", "Scotland", "South East"]
    treated = {"North West", "Wales"}
    dates = pd.date_range("2025-01-01", periods=90, freq="D")
    rows: list[dict[str, object]] = []
    for day_index, date_day in enumerate(dates):
        post = day_index >= 55
        for region in regions:
            is_treated = region in treated
            base = 4.0 + 0.02 * day_index + (0.7 if region in {"London", "South East"} else 0)
            treatment_lift = 2.5 if is_treated and post else 0.0
            referral_signups = base + treatment_lift + rng.normal(0, 0.05)
            rows.append(
                {
                    "region": region,
                    "date_day": date_day,
                    "treated_region": is_treated,
                    "post_period": post,
                    "incentive_active": is_treated and post,
                    "signups": 100 + day_index,
                    "referral_signups": referral_signups,
                    "incremental_signups_ground_truth": int(round(max(treatment_lift, 0))),
                    "reward_cost_gbp": 20.0 * max(treatment_lift, 0),
                }
            )
    return pd.DataFrame(rows)


def test_did_recovers_regional_treatment_lift() -> None:
    frame = _geo_panel()

    result = estimate_did(frame, "referral_signups")

    assert 2.2 < result.effect_per_region_day < 2.8
    assert result.ci_low < result.effect_per_region_day < result.ci_high


def test_parallel_trends_and_placebos_are_computable() -> None:
    frame = _geo_panel()

    trend_gap = parallel_trends_gap(frame, "referral_signups")
    placebos = placebo_did_by_region(frame, "referral_signups")

    assert abs(trend_gap) < 0.05
    assert not placebos.empty
    assert {"region", "effect_per_region_day", "p_value"}.issubset(placebos.columns)


def test_synthetic_control_recovers_positive_post_effect() -> None:
    frame = _geo_panel()

    result = estimate_synthetic_control(frame, "referral_signups")
    placebos = synthetic_control_placebos(frame, "referral_signups")

    assert result.post_effect_total > 100
    assert abs(result.donor_weights["weight"].sum() - 1) < 1e-6
    assert not placebos.empty


def test_referral_incrementality_memo_renders() -> None:
    frame = _geo_panel()

    run = analyse_referral_incrementality(frame, configured_incrementality_fraction=0.6)
    memo = render_markdown(run)

    assert "Referral Incrementality Geo Experiment" in memo
    assert run.blended_incremental_signups > 0
    assert run.observed_incremental_ground_truth > 0
