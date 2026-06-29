"""Segment-level customer-outcome and fairness-gap metrics.

These power the planned Customer Outcomes & Fairness view: they summarise how an
outcome (activation, complaint, support contact, failed onboarding, ...) varies
across a wellbeing or inclusion segment, and quantify the gap between the best- and
worst-served segments so harmful disparities are visible before a rollout decision.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class OutcomeGap:
    segment: str
    outcome: str
    best_level: str
    worst_level: str
    best_rate: float
    worst_rate: float
    gap: float


def segment_outcome_rates(
    frame: pd.DataFrame,
    segment: str,
    outcomes: list[str],
    *,
    min_segment_size: int = 1,
) -> pd.DataFrame:
    """Mean of each outcome per segment level, with the level's customer count.

    Boolean outcomes are treated as 0/1. Levels smaller than ``min_segment_size``
    are dropped so thin slices do not produce noisy or re-identifying rates.
    """

    if segment not in frame.columns:
        raise KeyError(f"segment column '{segment}' is not in the frame")
    missing = [outcome for outcome in outcomes if outcome not in frame.columns]
    if missing:
        raise KeyError(f"outcome columns not in frame: {missing}")

    working = frame.copy()
    for outcome in outcomes:
        working[outcome] = working[outcome].astype(float)

    aggregations = {outcome: (outcome, "mean") for outcome in outcomes}
    aggregations["customers"] = (segment, "size")
    grouped = (
        working.groupby(segment, dropna=False)
        .agg(**aggregations)
        .reset_index()
        .rename(columns={segment: "level"})
    )
    grouped = grouped[grouped["customers"] >= min_segment_size]
    grouped.insert(0, "segment", segment)
    return grouped.sort_values("level").reset_index(drop=True)


def outcome_gap(
    frame: pd.DataFrame,
    segment: str,
    outcome: str,
    *,
    min_segment_size: int = 1,
) -> OutcomeGap | None:
    """Gap between the highest- and lowest-rate levels of ``segment`` for ``outcome``.

    Returns ``None`` when fewer than two qualifying levels exist.
    """

    rates = segment_outcome_rates(
        frame, segment, [outcome], min_segment_size=min_segment_size
    )
    if len(rates) < 2:
        return None

    best_row = rates.loc[rates[outcome].idxmax()]
    worst_row = rates.loc[rates[outcome].idxmin()]
    return OutcomeGap(
        segment=segment,
        outcome=outcome,
        best_level=str(best_row["level"]),
        worst_level=str(worst_row["level"]),
        best_rate=float(best_row[outcome]),
        worst_rate=float(worst_row[outcome]),
        gap=float(best_row[outcome] - worst_row[outcome]),
    )
