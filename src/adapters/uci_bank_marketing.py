"""Real-data adapter: UCI Bank Marketing dataset.

Demonstrates that the platform's customer-outcome / fairness analysis runs on **real**
data, not only the synthetic engine. The dataset (Moro, Cortez & Rita, 2014) holds
~41k real phone-campaign records from a Portuguese bank, with a genuine conversion
outcome (term-deposit subscription) and demographic features for fairness slicing. It
also ships in ``fairlearn.datasets``, so it is an established fairness benchmark.

Download ``bank-additional-full.csv`` (or ``bank-full.csv``) from
https://archive.ics.uci.edu/dataset/222/bank+marketing and pass its path to
``load_bank_marketing``. The analysis reuses ``src.wellbeing.metrics.outcome_gap`` --
the same fairness machinery the synthetic dashboard uses.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.wellbeing.metrics import outcome_gap

# Demographic segments available in the dataset, used for fairness slicing.
SEGMENTS = ["age_band", "education", "marital", "job"]

_AGE_BINS = [0, 25, 35, 45, 55, 65, 200]
_AGE_LABELS = ["under_25", "25_34", "35_44", "45_54", "55_64", "65_plus"]


@dataclass(frozen=True)
class ConversionSummary:
    customers: int
    subscribed: int
    conversion_rate: float


def prepare(raw: pd.DataFrame) -> pd.DataFrame:
    """Standardise a raw UCI Bank Marketing frame for outcome/fairness analysis.

    Adds a boolean ``subscribed`` outcome and an ``age_band``; keeps the demographic
    segment columns. Works on any already-loaded frame, so it is testable offline.
    """
    frame = raw.copy()
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    if "y" not in frame.columns:
        raise KeyError("expected a 'y' target column (yes/no) in the UCI dataset")

    frame["subscribed"] = (
        frame["y"].astype(str).str.strip().str.lower() == "yes"
    )
    if "age" in frame.columns:
        frame["age"] = pd.to_numeric(frame["age"], errors="coerce")
        frame["age_band"] = pd.cut(
            frame["age"], bins=_AGE_BINS, labels=_AGE_LABELS, right=False
        ).astype("object")
    demographics = [c for c in ("job", "marital", "education") if c in frame.columns]
    keep = ["subscribed", "age", "age_band", *demographics]
    return frame[[c for c in keep if c in frame.columns]]


def load_bank_marketing(path: Path) -> pd.DataFrame:
    """Load and prepare the UCI Bank Marketing CSV (semicolon-separated)."""
    raw = pd.read_csv(path, sep=";", quotechar='"')
    return prepare(raw)


def conversion_summary(frame: pd.DataFrame) -> ConversionSummary:
    customers = len(frame)
    subscribed = int(frame["subscribed"].astype(bool).sum()) if customers else 0
    return ConversionSummary(
        customers=customers,
        subscribed=subscribed,
        conversion_rate=(subscribed / customers if customers else 0.0),
    )


def fairness_gaps(
    frame: pd.DataFrame,
    *,
    segments: list[str] | None = None,
    min_segment_size: int = 50,
) -> pd.DataFrame:
    """Subscription-rate disparity (pp) across each demographic segment.

    Reuses the synthetic platform's ``outcome_gap`` so the same fairness definition
    applies to real and synthetic data.
    """
    columns = ["segment", "gap_pp", "higher_rate_level", "lower_rate_level"]
    segments = segments or SEGMENTS
    if frame.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    for segment in segments:
        if segment not in frame.columns:
            continue
        gap = outcome_gap(frame, segment, "subscribed", min_segment_size=min_segment_size)
        if gap is None:
            continue
        rows.append(
            {
                "segment": segment,
                "gap_pp": round(gap.gap * 100, 2),
                "higher_rate_level": gap.best_level,
                "lower_rate_level": gap.worst_level,
            }
        )
    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values("gap_pp", ascending=False)
        .reset_index(drop=True)
    )


def render_markdown(frame: pd.DataFrame) -> str:
    summary = conversion_summary(frame)
    gaps = fairness_gaps(frame)
    lines = [
        "# UCI Bank Marketing - real-data fairness readout",
        "",
        f"- Records: `{summary.customers:,}`",
        f"- Term-deposit conversion: `{summary.conversion_rate:.1%}` "
        f"({summary.subscribed:,} subscribed)",
        "",
        "## Subscription-rate disparity by segment",
        "",
        "| Segment | Gap (pp) | Higher-rate level | Lower-rate level |",
        "| --- | ---: | --- | --- |",
    ]
    for row in gaps.itertuples(index=False):
        lines.append(
            f"| {row.segment} | {row.gap_pp:.1f} | "
            f"{row.higher_rate_level} | {row.lower_rate_level} |"
        )
    lines.extend(
        [
            "",
            "_Real data (UCI Bank Marketing, Moro et al. 2014), analysed with the same "
            "`outcome_gap` machinery used on the synthetic platform._",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the fairness/outcome analysis on the UCI Bank Marketing dataset."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to bank-additional-full.csv / bank-full.csv (semicolon-separated).",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    frame = load_bank_marketing(args.csv)
    report = render_markdown(frame)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote real-data readout to {args.output.resolve()}")
    else:
        print(report)


if __name__ == "__main__":
    main()
