"""Run the personalised onboarding A/B analysis and write the decision memo."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from src.experiments.analysis import (
    CupedResult,
    EffectEstimate,
    cuped_adjusted_effect,
    difference_in_means,
    heterogeneous_effects,
    sample_ratio_mismatch,
)
from src.experiments.guardrails import GuardrailResult, GuardrailSpec, evaluate_guardrails
from src.experiments.power import achieved_power_binary, binary_mde, sample_size_per_arm_binary

EXPERIMENT_NAME = "personalised_onboarding_pot_prompt"
PRIMARY_METRIC = "activated_d7"
CUPED_COVARIATE = "d7_activation_probability_control"


@dataclass(frozen=True)
class OnboardingAnalysis:
    row_count: int
    srm_p_value: float
    srm_passed: bool
    naive: EffectEstimate
    cuped: CupedResult
    achieved_power: float
    mde: float
    sample_size_for_two_pp: int
    guardrails: list[GuardrailResult]
    heterogeneity: pd.DataFrame
    true_lift_pp: float | None

    @property
    def recommendation(self) -> str:
        if not self.srm_passed:
            return "HOLD: assignment quality failed SRM."
        if any(not guardrail.passed for guardrail in self.guardrails):
            return "ITERATE: primary metric moved, but at least one guardrail needs review."
        if self.cuped.estimate.ci_low > 0:
            return "SHIP: launch the personalised prompt with rollout monitoring."
        return "HOLD: effect is not yet statistically clear."


def load_experiment_frame(db_path: Path, experiment_name: str = EXPERIMENT_NAME) -> pd.DataFrame:
    query = """
        select *
        from main_marts.fct_experiment_user_metrics
        where experiment_name = ?
    """
    with duckdb.connect(str(db_path), read_only=True) as con:
        frame = con.execute(query, [experiment_name]).fetchdf()
    if frame.empty:
        raise ValueError(f"No rows found for experiment {experiment_name!r}")
    return frame


def load_true_lift(db_path: Path) -> float | None:
    query = """
        select value
        from main_staging.stg_experiment_ground_truth
        where metric = 'personalised_onboarding_d7_activation_lift_pp'
    """
    with duckdb.connect(str(db_path), read_only=True) as con:
        rows = con.execute(query).fetchall()
    return float(rows[0][0]) if rows else None


def prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.copy()
    bool_metrics = [
        "activated_d7",
        "activated_ever",
        "adopted_savings_pot",
        "adopted_salary_sorter",
        "vulnerable_customer_flag",
        "push_opt_in",
        "business_account_flag",
    ]
    for column in bool_metrics:
        if column in prepared:
            prepared[column] = prepared[column].astype(float)
    prepared["has_support_contact"] = (prepared["support_contacts"] > 0).astype(float)
    prepared["has_complaint"] = (prepared["complaints"] > 0).astype(float)
    prepared["has_app_crash"] = (prepared["app_crashes"] > 0).astype(float)
    prepared["vulnerable_d7_activation"] = prepared["activated_d7"].where(
        prepared["vulnerable_customer_flag"] == 1.0
    )
    return prepared


def analyse_onboarding_experiment(
    frame: pd.DataFrame,
    *,
    true_lift_pp: float | None = None,
) -> OnboardingAnalysis:
    prepared = prepare_frame(frame)
    srm = sample_ratio_mismatch(prepared)
    naive = difference_in_means(prepared, PRIMARY_METRIC)
    cuped = cuped_adjusted_effect(prepared, PRIMARY_METRIC, CUPED_COVARIATE)

    guardrail_specs = [
        GuardrailSpec(
            metric="has_support_contact",
            label="Support contact rate",
            max_allowed_increase=0.005,
        ),
        GuardrailSpec(metric="has_complaint", label="Complaint rate", max_allowed_increase=0.002),
        GuardrailSpec(metric="has_app_crash", label="App crash rate", max_allowed_increase=0.010),
        GuardrailSpec(
            metric="vulnerable_d7_activation",
            label="Vulnerable-customer D7 activation",
            min_allowed_effect=-0.010,
        ),
    ]
    guardrails = [
        result
        for result in evaluate_guardrails(prepared.dropna(subset=["variant"]), guardrail_specs)
        if result.estimate.control_n > 1 and result.estimate.treatment_n > 1
    ]

    heterogeneity_frames = [
        heterogeneous_effects(prepared, PRIMARY_METRIC, segment)
        for segment in ["signup_channel", "income_segment", "region", "device_os"]
    ]
    heterogeneity = pd.concat(heterogeneity_frames, ignore_index=True).sort_values(
        "effect",
        ascending=False,
    )

    achieved_power = achieved_power_binary(
        naive.control_mean,
        cuped.estimate.effect,
        cuped.estimate.control_n,
        cuped.estimate.treatment_n,
    )
    mde = binary_mde(
        naive.control_mean,
        cuped.estimate.control_n,
        cuped.estimate.treatment_n,
    )
    sample_size_for_two_pp = sample_size_per_arm_binary(naive.control_mean, 0.02)

    return OnboardingAnalysis(
        row_count=len(prepared),
        srm_p_value=srm.p_value,
        srm_passed=srm.passed,
        naive=naive,
        cuped=cuped,
        achieved_power=achieved_power,
        mde=mde,
        sample_size_for_two_pp=sample_size_for_two_pp,
        guardrails=guardrails,
        heterogeneity=heterogeneity,
        true_lift_pp=true_lift_pp,
    )


def _pct(value: float) -> str:
    return f"{100 * value:.2f}%"


def _pp(value: float) -> str:
    return f"{100 * value:.2f} pp"


def render_markdown(analysis: OnboardingAnalysis) -> str:
    top_segments = analysis.heterogeneity.head(6)
    guardrail_rows = "\n".join(
        "- "
        f"{result.spec.label}: effect {_pp(result.estimate.effect)}, "
        f"95% CI [{_pp(result.estimate.ci_low)}, {_pp(result.estimate.ci_high)}], "
        f"{'pass' if result.passed else 'review'} ({result.reason})."
        for result in analysis.guardrails
    )
    heterogeneity_rows = "\n".join(
        "- "
        f"{row.segment} = {row.level}: effect {_pp(row.effect)}, "
        f"95% CI [{_pp(row.ci_low)}, {_pp(row.ci_high)}], "
        f"n={int(row.control_n + row.treatment_n):,}."
        for row in top_segments.itertuples(index=False)
    )
    true_lift = (
        f"The embedded synthetic ground truth is {_pp(analysis.true_lift_pp)}."
        if analysis.true_lift_pp is not None
        else "No embedded ground-truth lift was available."
    )
    assignment_status = "passed" if analysis.srm_passed else "failed"
    naive_line = (
        f"- Naive lift: {_pp(analysis.naive.effect)}, "
        f"95% CI [{_pp(analysis.naive.ci_low)}, {_pp(analysis.naive.ci_high)}], "
        f"p={analysis.naive.p_value:.4f}."
    )
    cuped_line = (
        f"- CUPED lift: {_pp(analysis.cuped.estimate.effect)}, "
        "95% CI "
        f"[{_pp(analysis.cuped.estimate.ci_low)}, "
        f"{_pp(analysis.cuped.estimate.ci_high)}], "
        f"p={analysis.cuped.estimate.p_value:.4f}."
    )
    cuped_diagnostics = (
        f"- CUPED theta: {analysis.cuped.theta:.4f}; "
        f"variance reduction: {_pct(analysis.cuped.variance_reduction)}."
    )

    return f"""# Decision Memo: Personalised Onboarding A/B Test

## Executive Summary

{analysis.recommendation}

The treatment increased D7 activation by {_pp(analysis.cuped.estimate.effect)} with CUPED,
95% CI [{_pp(analysis.cuped.estimate.ci_low)}, {_pp(analysis.cuped.estimate.ci_high)}],
p={analysis.cuped.estimate.p_value:.4f}. {true_lift}

## Context

We tested a personalised onboarding prompt that nudges new users toward a Savings Pot
setup flow. The decision metric is D7 activation: first card transaction within 7
days of signup. The experiment uses deterministic 50/50 assignment at signup and a
pre-treatment activation propensity score from signup metadata as the CUPED covariate.

## Assignment Quality And Power

- Analysed users: {analysis.row_count:,}.
- SRM p-value: {analysis.srm_p_value:.4f}; {assignment_status} at alpha 0.001.
- Current 80% power MDE: {_pp(analysis.mde)} absolute D7 activation lift.
- Approximate achieved power for the CUPED estimate: {_pct(analysis.achieved_power)}.
- Balanced sample needed per arm for a 2.00 pp lift: {analysis.sample_size_for_two_pp:,}.

## Result

- Control D7 activation: {_pct(analysis.naive.control_mean)}.
- Treatment D7 activation: {_pct(analysis.naive.treatment_mean)}.
{naive_line}
{cuped_line}
{cuped_diagnostics}

## Guardrails

{guardrail_rows}

## Heterogeneous Effects

Largest positive slices:

{heterogeneity_rows}

## Caveats

The CUPED covariate is a synthetic pre-treatment propensity score. In a live fintech
setting, the same pattern should use frozen pre-experiment or eligibility-time
features from governed feature tables, with no leakage from treatment exposure.
The analysis reads user-level marts, so rollout monitoring should still validate
support load, complaints, app stability, and vulnerable-customer outcomes in daily
dashboards before ramping to full traffic.

## Recommendation

{analysis.recommendation}

Roll out behind a feature flag, monitor the guardrails above daily for the first two
weeks, and keep the personalised prompt eligible only for users whose onboarding
state makes the prompt clearly relevant.

## Next Experiment

Test prompt timing and message framing: immediate post-signup versus after first app
session, with separate treatment arms for Savings Pot setup, Salary Sorter setup,
and a neutral "make your first card payment" activation prompt.
"""


def write_memo(analysis: OnboardingAnalysis, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(analysis), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the onboarding A/B experiment analysis.")
    parser.add_argument("--db", type=Path, default=Path("neobank.duckdb"))
    parser.add_argument("--output", type=Path, default=Path("docs/memos/MEMO_AB_ONBOARDING.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = load_experiment_frame(args.db)
    true_lift = load_true_lift(args.db)
    analysis = analyse_onboarding_experiment(frame, true_lift_pp=true_lift)
    write_memo(analysis, args.output)
    print(f"Wrote onboarding experiment memo to {args.output}")
    print(analysis.recommendation)


if __name__ == "__main__":
    main()
