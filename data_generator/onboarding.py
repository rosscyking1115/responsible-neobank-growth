"""Synthetic onboarding / KYC funnel events.

Models a sequential onboarding funnel (signup -> identity check started -> identity
check passed -> card activated) where drop-off is correlated with digital confidence,
new-to-UK status, and accessibility need. This is the data foundation for digital
inclusion analysis: who fails onboarding and who needs an assisted journey.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from data_generator.config import GeneratorConfig

ONBOARDING_SEED_OFFSET = 202

# Ordered funnel steps. Every signed-up user reaches "signup_started".
FUNNEL_STEPS = [
    "signup_started",
    "identity_check_started",
    "identity_check_passed",
    "card_activated",
]


def _clip(values: np.ndarray, low: float, high: float) -> np.ndarray:
    return np.clip(values, low, high)


def generate_onboarding_events(
    users: pl.DataFrame,
    wellbeing: pl.DataFrame,
    config: GeneratorConfig,
) -> pl.DataFrame:
    """Per-user onboarding funnel outcomes, correlated with wellbeing proxies."""

    rng = np.random.default_rng(config.seed + ONBOARDING_SEED_OFFSET)
    n = users.height

    user_id = users.get_column("user_id").to_numpy()
    # wellbeing is generated from the same users frame in the same row order.
    dc = wellbeing.get_column("digital_confidence_score").to_numpy()
    accessibility = wellbeing.get_column("accessibility_need_proxy").to_numpy().astype(bool)
    new_to_uk = wellbeing.get_column("new_to_uk_proxy").to_numpy().astype(bool)

    p_start = _clip(0.90 + 0.08 * dc - 0.05 * new_to_uk, 0.50, 0.999)
    p_pass = _clip(0.78 + 0.18 * dc - 0.12 * new_to_uk - 0.05 * accessibility, 0.30, 0.99)
    p_activate = _clip(0.82 + 0.15 * dc - 0.04 * accessibility, 0.40, 0.99)

    started = rng.random(n) < p_start
    passed = started & (rng.random(n) < p_pass)
    activated = passed & (rng.random(n) < p_activate)
    completed = activated

    furthest_step = np.where(
        ~started,
        "signup_started",
        np.where(
            ~passed,
            "identity_check_started",
            np.where(~activated, "identity_check_passed", "card_activated"),
        ),
    ).tolist()
    # Nullable string column: the step a customer stalled at, or null if completed.
    abandoned_step = [
        None if is_complete else step
        for is_complete, step in zip(completed, furthest_step, strict=True)
    ]
    needs_assisted_onboarding = (~completed) & (
        (dc < 0.50) | accessibility | new_to_uk
    )

    return pl.DataFrame(
        {
            "user_id": user_id,
            "identity_check_started": started,
            "identity_check_passed": passed,
            "card_activated": activated,
            "completed_onboarding": completed,
            "furthest_step": furthest_step,
            "abandoned_step": abandoned_step,
            "needs_assisted_onboarding": needs_assisted_onboarding,
        }
    )
