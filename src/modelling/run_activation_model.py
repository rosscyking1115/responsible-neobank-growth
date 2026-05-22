"""Train the activation decisioning model and write a model card."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.modelling.evaluate import (
    GuardrailCheck,
    ModelMetrics,
    ThresholdResult,
    choose_threshold,
    classification_metrics,
    customer_outcome_guardrails,
    threshold_sweep,
)
from src.modelling.explain import coefficient_importance, segment_score_summary
from src.modelling.features import (
    activated_user_value,
    feature_matrix,
    load_activation_frame,
    target_vector,
    temporal_train_calibration_test_split,
)
from src.modelling.train import CalibratedActivationModel, fit_calibrated_activation_model


@dataclass(frozen=True)
class ActivationModelRun:
    rows: int
    train_rows: int
    calibration_rows: int
    test_rows: int
    value_per_activation_gbp: float
    metrics: ModelMetrics
    threshold: ThresholdResult
    guardrails: list[GuardrailCheck]
    importance: pd.DataFrame
    segment_summary: pd.DataFrame

    @property
    def recommendation(self) -> str:
        if any(not check.passed for check in self.guardrails):
            return "ITERATE: model performance is usable, but a customer-outcome guardrail failed."
        if self.metrics.roc_auc < 0.55 or self.metrics.expected_calibration_error > 0.05:
            return "HOLD: calibration or rank ordering is not strong enough for decisioning."
        if self.threshold.expected_net_value_gbp <= 0:
            return "HOLD: no positive-value targeting threshold was found."
        return "PILOT: use the model for a monitored onboarding-help treatment."


def train_and_evaluate(db_path: Path) -> tuple[ActivationModelRun, CalibratedActivationModel]:
    frame = load_activation_frame(db_path)
    split = temporal_train_calibration_test_split(frame)
    model = fit_calibrated_activation_model(split.train, split.calibration)
    test_probabilities = model.predict_proba(feature_matrix(split.test))
    metrics = classification_metrics(target_vector(split.test), test_probabilities)
    value_per_activation = activated_user_value(split.train)
    thresholds = threshold_sweep(
        split.test,
        test_probabilities,
        value_per_activation_gbp=value_per_activation,
    )
    threshold = choose_threshold(thresholds)
    guardrails = customer_outcome_guardrails(split.test, test_probabilities, threshold.threshold)
    importance = coefficient_importance(model)
    segment_summary = segment_score_summary(split.test, test_probabilities, "signup_channel")
    run = ActivationModelRun(
        rows=len(frame),
        train_rows=len(split.train),
        calibration_rows=len(split.calibration),
        test_rows=len(split.test),
        value_per_activation_gbp=value_per_activation,
        metrics=metrics,
        threshold=threshold,
        guardrails=guardrails,
        importance=importance,
        segment_summary=segment_summary,
    )
    return run, model


def _pct(value: float) -> str:
    return f"{100 * value:.2f}%"


def _gbp(value: float) -> str:
    return f"GBP {value:,.0f}"


def render_model_card(run: ActivationModelRun) -> str:
    guardrail_rows = "\n".join(
        "- "
        f"{check.name}: {check.value:.3f} {check.direction} {check.limit:.3f} "
        f"({'pass' if check.passed else 'review'})."
        for check in run.guardrails
    )
    split_line = (
        f"- Temporal split: {run.train_rows:,} train, "
        f"{run.calibration_rows:,} calibration, {run.test_rows:,} test."
    )
    targeted_line = (
        f"- Targeted users in test window: {run.threshold.targeted_users:,} "
        f"({_pct(run.threshold.targeting_rate)})."
    )
    importance_rows = "\n".join(
        "- "
        f"{row.feature}: coefficient {row.coefficient:.3f} "
        f"(absolute {row.absolute_coefficient:.3f})."
        for row in run.importance.itertuples(index=False)
    )
    segment_rows = "\n".join(
        "- "
        f"{row.signup_channel}: mean score {_pct(row.mean_score)}, "
        f"observed D7 activation {_pct(row.activation_rate)}, rows {int(row.rows):,}."
        for row in run.segment_summary.itertuples(index=False)
    )
    return f"""# Model Card: Activation Decisioning

## Executive Summary

{run.recommendation}

The calibrated signup-time model ranks D7 activation propensity with ROC AUC
{run.metrics.roc_auc:.3f}, Brier score {run.metrics.brier_score:.3f}, and expected
calibration error {_pct(run.metrics.expected_calibration_error)} on the forward test
window. The best threshold targets users with predicted activation probability at
or below {_pct(run.threshold.threshold)}.

## Intended Use

Use this model to prioritise a helpful onboarding intervention, such as extra setup
guidance or a clearer first-card-payment prompt. The score should not be used for
pricing, eligibility, credit decisions, account limits, or any punitive customer
treatment.

## Data And Features

- Rows: {run.rows:,}.
{split_line}
- Label: D7 activation, defined as first card transaction within 7 days of signup.
- Features: region, signup channel, device OS, age, income segment, push opt-in,
  vulnerable-customer flag, business-account flag, signup month, and signup day of week.
- Excluded from training: transaction outcomes, feature adoption, support contacts,
  CLV, experiment treatment, and synthetic hidden propensity fields.

## Performance

- Test rows: {run.metrics.rows:,}.
- Test activation rate: {_pct(run.metrics.activation_rate)}.
- ROC AUC: {run.metrics.roc_auc:.3f}.
- Average precision: {run.metrics.average_precision:.3f}.
- Brier score: {run.metrics.brier_score:.3f}.
- Log loss: {run.metrics.log_loss:.3f}.
- Expected calibration error: {_pct(run.metrics.expected_calibration_error)}.

## Threshold Economics

- Value per activation assumption: {_gbp(run.value_per_activation_gbp)}.
- Contact cost assumption: GBP 0.45 per targeted user.
- Selected threshold: predicted activation <= {_pct(run.threshold.threshold)}.
{targeted_line}
- Expected incremental activations: {run.threshold.expected_incremental_activations:,.1f}.
- Expected net value: {_gbp(run.threshold.expected_net_value_gbp)}.

## Customer-Outcome Guardrails

{guardrail_rows}

These checks are deliberately conservative. A live rollout should also monitor
complaints, support contacts, opt-outs, accessibility needs, and vulnerable-customer
outcomes daily.

## Explainability

Largest model coefficients after preprocessing:

{importance_rows}

Signup-channel score summary:

{segment_rows}

## Operating Policy

The model should be deployed only behind an experiment or feature flag. Use it to
offer assistance, not to withhold service. Recalibrate monthly or whenever acquisition
mix changes materially, and retrain if expected calibration error exceeds 5% or if
any customer-outcome guardrail fails.
"""


def write_model_card(run: ActivationModelRun, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_model_card(run), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train activation decisioning model.")
    parser.add_argument("--db", type=Path, default=Path("neobank.duckdb"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/model_cards/MODEL_ACTIVATION_DECISIONING.md"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run, _model = train_and_evaluate(args.db)
    write_model_card(run, args.output)
    print(f"Wrote activation model card to {args.output}")
    print(run.recommendation)


if __name__ == "__main__":
    main()
