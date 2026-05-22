"""Run regional referral incrementality analysis and write the decision memo."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from src.experiments.did import DidResult, estimate_did, parallel_trends_gap, placebo_did_by_region
from src.experiments.synthetic_control import (
    SyntheticControlResult,
    estimate_synthetic_control,
    synthetic_control_placebos,
)

REFERRAL_METRIC = "referral_signups"
TOTAL_SIGNUP_METRIC = "signups"
REWARD_PER_SIDE_GBP = 10


@dataclass(frozen=True)
class ReferralIncrementalityRun:
    rows: int
    treated_regions: list[str]
    post_days: int
    did: DidResult
    synthetic_control: SyntheticControlResult
    signup_spillover: DidResult
    parallel_trends_gap: float
    placebo_did: pd.DataFrame
    placebo_synthetic_control: pd.DataFrame
    observed_incremental_ground_truth: int
    observed_reward_cost_gbp: float
    configured_incrementality_fraction: float | None

    @property
    def blended_incremental_signups(self) -> float:
        did_total = self.did.effect_per_region_day * len(self.treated_regions) * self.post_days
        return (did_total + self.synthetic_control.post_effect_total) / 2

    @property
    def cost_per_incremental_signup_gbp(self) -> float:
        if self.blended_incremental_signups <= 0:
            return float("inf")
        return self.observed_reward_cost_gbp / self.blended_incremental_signups

    @property
    def ground_truth_recovery_ratio(self) -> float:
        if self.observed_incremental_ground_truth == 0:
            return 0.0
        return self.blended_incremental_signups / self.observed_incremental_ground_truth

    @property
    def recommendation(self) -> str:
        suspicious_spillover = (
            self.signup_spillover.p_value < 0.05
            and abs(self.signup_spillover.effect_per_region_day) > 2
        )
        if suspicious_spillover:
            return "ITERATE: referral lift is positive, but total-signup spillover needs review."
        if self.blended_incremental_signups <= 0:
            return "HOLD: causal estimates do not show positive incrementality."
        if self.cost_per_incremental_signup_gbp <= 35:
            return "SHIP: expand the regional referral incentive with monitoring."
        return "ITERATE: referral lift is positive, but unit economics need a cheaper incentive."


def load_referral_panel(db_path: Path) -> pd.DataFrame:
    query = """
        select *
        from main_marts.fct_region_daily_referrals
    """
    with duckdb.connect(str(db_path), read_only=True) as con:
        frame = con.execute(query).fetchdf()
    if frame.empty:
        raise ValueError("No rows found in fct_region_daily_referrals")
    frame["date_day"] = pd.to_datetime(frame["date_day"])
    return frame


def load_configured_incrementality(db_path: Path) -> float | None:
    query = """
        select value
        from main_staging.stg_experiment_ground_truth
        where metric = 'referral_incrementality_fraction'
    """
    with duckdb.connect(str(db_path), read_only=True) as con:
        rows = con.execute(query).fetchall()
    return float(rows[0][0]) if rows else None


def analyse_referral_incrementality(
    frame: pd.DataFrame,
    *,
    configured_incrementality_fraction: float | None = None,
) -> ReferralIncrementalityRun:
    did = estimate_did(frame, REFERRAL_METRIC)
    synthetic_control = estimate_synthetic_control(frame, REFERRAL_METRIC)
    signup_spillover = estimate_did(frame, TOTAL_SIGNUP_METRIC)
    trend_gap = parallel_trends_gap(frame, REFERRAL_METRIC)
    placebo_did = placebo_did_by_region(frame, REFERRAL_METRIC)
    placebo_sc = synthetic_control_placebos(frame, REFERRAL_METRIC)
    post = frame.loc[frame["post_period"]]
    treated_regions = sorted(frame.loc[frame["treated_region"], "region"].unique())
    return ReferralIncrementalityRun(
        rows=len(frame),
        treated_regions=treated_regions,
        post_days=int(frame.loc[frame["post_period"], "date_day"].nunique()),
        did=did,
        synthetic_control=synthetic_control,
        signup_spillover=signup_spillover,
        parallel_trends_gap=trend_gap,
        placebo_did=placebo_did,
        placebo_synthetic_control=placebo_sc,
        observed_incremental_ground_truth=int(post["incremental_signups_ground_truth"].sum()),
        observed_reward_cost_gbp=float(post["reward_cost_gbp"].sum()),
        configured_incrementality_fraction=configured_incrementality_fraction,
    )


def _n(value: float) -> str:
    return f"{value:,.1f}"


def _gbp(value: float) -> str:
    return f"GBP {value:,.0f}"


def render_markdown(run: ReferralIncrementalityRun) -> str:
    did_total = run.did.effect_per_region_day * len(run.treated_regions) * run.post_days
    max_placebo_did = float(run.placebo_did["effect_per_region_day"].abs().max())
    max_placebo_sc = float(run.placebo_synthetic_control["post_effect_total"].abs().max())
    top_weights = "\n".join(
        f"- {row.region}: {100 * row.weight:.1f}%"
        for row in run.synthetic_control.donor_weights.head(5).itertuples(index=False)
    )
    placebo_rows = "\n".join(
        "- "
        f"{row.region}: DiD {row.effect_per_region_day:.2f} referral signups per day, "
        f"synthetic-control total {row.post_effect_total:.1f}."
        for row in (
            run.placebo_did.merge(
                run.placebo_synthetic_control[["region", "post_effect_total"]],
                on="region",
            )
            .head(5)
            .itertuples(index=False)
        )
    )
    configured = (
        f"Configured synthetic incrementality fraction: "
        f"{100 * run.configured_incrementality_fraction:.1f}%."
        if run.configured_incrementality_fraction is not None
        else "Configured synthetic incrementality fraction was not available."
    )
    return f"""# Decision Memo: Referral Incrementality Geo Experiment

## TL;DR

{run.recommendation}

The blended causal estimate is {_n(run.blended_incremental_signups)} incremental
referral signups across {', '.join(run.treated_regions)} during the post period.
Observed reward cost was {_gbp(run.observed_reward_cost_gbp)}, implying
{_gbp(run.cost_per_incremental_signup_gbp)} per incremental signup.

## Context

We tested a regional referral incentive in selected regions where network effects
make a user-level A/B test hard to interpret. The outcome is referral-attributed
signups per region-day. Total signups are monitored as a spillover guardrail.

## Result

- DiD effect: {run.did.effect_per_region_day:.2f} referral signups per treated region-day,
  95% CI [{run.did.ci_low:.2f}, {run.did.ci_high:.2f}], p={run.did.p_value:.4f}.
- DiD total lift: {_n(did_total)} referral signups.
- Synthetic-control total lift: {_n(run.synthetic_control.post_effect_total)} referral signups.
- Synthetic-control pre-period RMSE: {run.synthetic_control.pre_rmse:.2f}.
- Blended lift: {_n(run.blended_incremental_signups)} referral signups.
- Embedded ground-truth incremental referral signups observed in treated post period:
  {run.observed_incremental_ground_truth:,}. {configured}
- Ground-truth recovery ratio: {100 * run.ground_truth_recovery_ratio:.1f}%.

## Donor Pool

Largest synthetic-control donor weights:

{top_weights}

## Diagnostics

- Pre-period treated-minus-control slope gap: {run.parallel_trends_gap:.4f}
  referral signups per day.
- Total-signup spillover DiD: {run.signup_spillover.effect_per_region_day:.2f}
  signups per treated region-day, p={run.signup_spillover.p_value:.4f}.
- Largest absolute placebo DiD effect: {max_placebo_did:.2f} referral signups per day.
- Largest absolute placebo synthetic-control total effect: {_n(max_placebo_sc)} referral signups.

Placebo examples:

{placebo_rows}

## Caveats

The design assumes untreated regions form a credible counterfactual after controlling
for region and date effects. Remaining risks are cross-region referral spillovers,
region-specific marketing shocks, donor-pool mismatch, and seasonality not captured
by shared date effects. The synthetic-control estimate is useful as a triangulation
check, not as a proof by itself.

## Recommendation

{run.recommendation}

Roll out to additional similar regions in a stepped-wedge design, keep at least a few
regions as holdouts, and monitor total signups, referral quality, support contacts,
and cost per activated referred customer.

## Next Experiment

Test lower-cost incentive variants and message framing. The next readout should use
activated referred customers, not only referred signups, as the primary value metric.
"""


def write_memo(run: ReferralIncrementalityRun, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(run), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run referral incrementality geo analysis.")
    parser.add_argument("--db", type=Path, default=Path("neobank.duckdb"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/memos/MEMO_REFERRAL_INCREMENTALITY.md"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = load_referral_panel(args.db)
    configured_incrementality = load_configured_incrementality(args.db)
    run = analyse_referral_incrementality(
        frame,
        configured_incrementality_fraction=configured_incrementality,
    )
    write_memo(run, args.output)
    print(f"Wrote referral incrementality memo to {args.output}")
    print(run.recommendation)


if __name__ == "__main__":
    main()
