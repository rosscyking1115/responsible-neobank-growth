"""Non-circularity guards: the analysis must not read the generator's own answers.

The synthetic generator embeds a *ground truth* (``true_d7_lift_pp``,
``referral_incrementality``) and latent parameters (segment priors, config knobs). Those
exist so the causal / fairness methods can be **validated against** a known answer -- not
so the analysis can read the answer off the label. These tests pin that separation: the
estimators follow the *observed* data and are invariant to the presence (or a deliberately
wrong value) of any ground-truth / generator-only column. See docs/CREDIBILITY.md.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from src.experiments.analysis import cuped_adjusted_effect, difference_in_means
from src.release_decisions.decision_engine import ReleaseSignals
from src.wellbeing.metrics import outcome_gap

# Columns produced by the generator that the analysis must never consume as an input.
GENERATOR_ONLY_COLUMNS = {
    "true_d7_lift_pp",
    "d7_treatment_lift",
    "referral_incrementality",
    "assignment_bucket",
    "seed",
}


def _ab_frame() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 1_000
    variant = np.where(rng.random(n) < 0.5, "treatment", "control")
    # Observed activation with a real +6pp gap baked into the *data*, not a label.
    prob = np.where(variant == "treatment", 0.56, 0.50)
    activated = (rng.random(n) < prob).astype(float)
    covariate = rng.normal(size=n)
    return pd.DataFrame({"variant": variant, "activated": activated, "pre_activity": covariate})


def test_difference_in_means_ignores_a_bogus_ground_truth_column() -> None:
    frame = _ab_frame()
    baseline = difference_in_means(frame, "activated").effect

    # Inject a ground-truth column with a deliberately WRONG value. If the estimator
    # were circular it would be tempted by it; it must ignore it entirely.
    poisoned = frame.assign(true_d7_lift_pp=99.0)
    with_label = difference_in_means(poisoned, "activated").effect

    assert with_label == baseline
    # And the estimate reflects the observed ~+6pp gap, not the 99 label.
    assert abs(baseline) < 0.2


def test_cuped_ignores_a_bogus_ground_truth_column() -> None:
    frame = _ab_frame()
    baseline = cuped_adjusted_effect(frame, "activated", "pre_activity").estimate.effect
    poisoned = frame.assign(referral_incrementality=1.0, true_d7_lift_pp=-5.0)
    with_label = cuped_adjusted_effect(poisoned, "activated", "pre_activity").estimate.effect
    assert with_label == baseline


def test_outcome_gap_ignores_generator_latent_columns() -> None:
    rng = np.random.default_rng(1)
    n = 600
    segment = rng.choice(["low", "medium", "high"], size=n)
    outcome = (rng.random(n) < np.where(segment == "low", 0.3, 0.5)).astype(float)
    frame = pd.DataFrame({"income_band": segment, "activated": outcome})

    baseline = outcome_gap(frame, "income_band", "activated")
    poisoned = frame.assign(true_d7_lift_pp=42.0, d7_treatment_lift=0.99)
    with_latent = outcome_gap(poisoned, "income_band", "activated")

    assert baseline is not None and with_latent is not None
    assert with_latent.gap == baseline.gap
    assert with_latent.best_level == baseline.best_level


def test_release_signals_carry_no_generator_only_fields() -> None:
    """The decision engine's inputs must all be analysis-derived, observable signals."""
    field_names = {f.name for f in dataclasses.fields(ReleaseSignals)}
    leaked = field_names & GENERATOR_ONLY_COLUMNS
    assert not leaked, f"release inputs leak generator-only fields: {leaked}"
