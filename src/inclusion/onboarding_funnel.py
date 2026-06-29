"""Onboarding funnel conversion and digital-exclusion analysis.

Answers the inclusion questions a responsible neobank should ask: where do customers
drop out of onboarding, which segments are underserved, and who should be offered an
assisted journey rather than left to fail.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# Ordered funnel: each step is a boolean column on the customer-level frame, with
# every customer implicitly having reached "signup_started".
FUNNEL_STEPS = [
    "identity_check_started",
    "identity_check_passed",
    "card_activated",
]
FUNNEL_STEP_LABELS = {
    "signup_started": "Signed up",
    "identity_check_started": "Identity started",
    "identity_check_passed": "Identity passed",
    "card_activated": "Card activated",
}


@dataclass(frozen=True)
class AssistedOnboardingFlag:
    segment: str
    level: str
    completion_rate: float
    abandonment_rate: float
    customers: int


def funnel_conversion(
    frame: pd.DataFrame,
    *,
    steps: list[str] | None = None,
) -> pd.DataFrame:
    """Step-by-step funnel with overall reach and step-over-step conversion.

    Returns one row per step with the count reaching it, the overall rate (of all
    customers), and the conversion from the previous step.
    """
    steps = steps or FUNNEL_STEPS
    total = len(frame)
    columns = ["step", "label", "reached", "overall_rate", "step_conversion"]
    if total == 0:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    previous = total  # everyone starts at "signup_started"
    rows.append(
        {
            "step": "signup_started",
            "label": FUNNEL_STEP_LABELS["signup_started"],
            "reached": total,
            "overall_rate": 1.0,
            "step_conversion": 1.0,
        }
    )
    for step in steps:
        reached = int(frame[step].astype(bool).sum())
        rows.append(
            {
                "step": step,
                "label": FUNNEL_STEP_LABELS.get(step, step),
                "reached": reached,
                "overall_rate": reached / total,
                "step_conversion": (reached / previous) if previous else 0.0,
            }
        )
        previous = reached
    return pd.DataFrame(rows, columns=columns)


def abandonment_by_segment(
    frame: pd.DataFrame,
    segment: str,
    *,
    completion_column: str = "completed_onboarding",
    assisted_column: str = "needs_assisted_onboarding",
    min_segment_size: int = 30,
) -> pd.DataFrame:
    """Completion, abandonment, and assisted-need rates per segment level."""
    if segment not in frame.columns:
        raise KeyError(f"segment column '{segment}' is not in the frame")
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "segment",
                "level",
                "customers",
                "completion_rate",
                "abandonment_rate",
                "assisted_need_rate",
            ]
        )

    working = frame.copy()
    working[completion_column] = working[completion_column].astype(float)
    if assisted_column in working.columns:
        working[assisted_column] = working[assisted_column].astype(float)

    aggregations = {
        "customers": (completion_column, "size"),
        "completion_rate": (completion_column, "mean"),
    }
    if assisted_column in working.columns:
        aggregations["assisted_need_rate"] = (assisted_column, "mean")

    grouped = (
        working.groupby(segment, dropna=False)
        .agg(**aggregations)
        .reset_index()
        .rename(columns={segment: "level"})
    )
    grouped = grouped[grouped["customers"] >= min_segment_size]
    grouped["abandonment_rate"] = 1.0 - grouped["completion_rate"]
    grouped.insert(0, "segment", segment)
    if "assisted_need_rate" not in grouped.columns:
        grouped["assisted_need_rate"] = 0.0
    return grouped.sort_values("abandonment_rate", ascending=False).reset_index(drop=True)


def assisted_onboarding_segments(
    frame: pd.DataFrame,
    segment: str,
    *,
    max_acceptable_abandonment: float = 0.25,
    min_segment_size: int = 30,
) -> list[AssistedOnboardingFlag]:
    """Segment levels whose abandonment exceeds the acceptable threshold.

    These are the candidates for an assisted-onboarding variant rather than being
    left to fail the standard journey.
    """
    summary = abandonment_by_segment(frame, segment, min_segment_size=min_segment_size)
    flags: list[AssistedOnboardingFlag] = []
    for row in summary.itertuples(index=False):
        if row.abandonment_rate > max_acceptable_abandonment:
            flags.append(
                AssistedOnboardingFlag(
                    segment=segment,
                    level=str(row.level),
                    completion_rate=float(row.completion_rate),
                    abandonment_rate=float(row.abandonment_rate),
                    customers=int(row.customers),
                )
            )
    return flags
