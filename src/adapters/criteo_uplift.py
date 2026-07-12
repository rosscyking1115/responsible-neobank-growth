"""Real-data adapter: Criteo Uplift dataset.

A second real-data cross-check, aimed at the **experiment** chapter the way the UCI
adapter is aimed at the fairness chapter. The Criteo Uplift dataset (Diemert et al.,
2018) holds ~13M rows from a **real randomised** advertising experiment: a
``treatment`` flag (exposed to the campaign vs held out) and binary ``conversion`` /
``visit`` outcomes, plus 12 anonymised dense user features ``f0``..``f11``.

Why it earns its place: it lets the platform's own experiment machinery
(:func:`src.experiments.analysis.difference_in_means`,
:func:`~src.experiments.analysis.cuped_adjusted_effect`,
:func:`~src.experiments.analysis.sample_ratio_mismatch`) run on a **real** treatment /
control split, not only the synthetic engine.

**Honest boundary — read this.** This is *ad-tech, not fintech*, and — unlike the
synthetic geo/onboarding chapters — there is **no known ground-truth lift** to recover.
So it validates that the estimators *behave correctly on real randomised data*
(sensible effect, CUPED variance reduction, clean SRM); it does **not** validate
recovery of a true effect. That recovery check is exactly what the synthetic
synthetic-control chapter exists for, and why the core stays synthetic.

Download ``criteo-uplift-v2.1.csv`` from
https://ailab.criteo.com/criteo-uplift-prediction-dataset/ and pass its path to
:func:`load_criteo`. The file is large; use ``sample_rows`` / ``sample_frac`` to work
on a slice.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.experiments.analysis import (
    CupedResult,
    EffectEstimate,
    SrmResult,
    cuped_adjusted_effect,
    difference_in_means,
    sample_ratio_mismatch,
)

# Candidate anonymised pre-randomisation user features usable as a CUPED covariate.
FEATURE_COLUMNS = [f"f{i}" for i in range(12)]
# Binary experiment outcomes carried by the dataset.
OUTCOME_COLUMNS = ["conversion", "visit"]


@dataclass(frozen=True)
class CriteoReadout:
    metric: str
    covariate: str
    naive: EffectEstimate
    cuped: CupedResult
    srm: SrmResult


def prepare(raw: pd.DataFrame) -> pd.DataFrame:
    """Standardise a raw Criteo Uplift frame for the experiment machinery.

    Maps the ``treatment`` flag (0/1) onto the ``variant`` column the experiment
    functions expect (``control`` / ``treatment``), coerces the outcomes and features
    to numeric, and keeps only the columns the readout needs. Works on any already
    loaded frame, so it is testable offline.
    """
    frame = raw.copy()
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    if "treatment" not in frame.columns:
        raise KeyError("expected a 'treatment' column (0/1) in the Criteo dataset")
    outcomes = [c for c in OUTCOME_COLUMNS if c in frame.columns]
    if not outcomes:
        raise KeyError("expected at least one of 'conversion' / 'visit' outcome columns")

    treatment = pd.to_numeric(frame["treatment"], errors="coerce")
    frame["variant"] = treatment.map({1: "treatment", 0: "control"})
    for column in outcomes:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)
    features = [c for c in FEATURE_COLUMNS if c in frame.columns]
    for column in features:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    keep = ["variant", *outcomes, *features]
    prepared = frame[keep].dropna(subset=["variant"])
    return prepared.reset_index(drop=True)


def load_criteo(
    path: Path,
    *,
    sample_rows: int | None = None,
    sample_frac: float | None = None,
    seed: int = 13,
) -> pd.DataFrame:
    """Load and prepare the Criteo Uplift CSV (comma-separated, ~13M rows).

    Pass ``sample_rows`` to read only the first N rows (cheap), or ``sample_frac`` to
    draw a random fraction (a representative slice). ``sample_rows`` wins if both are
    given.
    """
    if sample_rows is not None:
        raw = pd.read_csv(path, nrows=sample_rows)
    elif sample_frac is not None:
        rng = random.Random(seed)
        # Skip rows probabilistically, always keeping the header (row 0).
        raw = pd.read_csv(
            path,
            skiprows=lambda i: i > 0 and rng.random() > sample_frac,
        )
    else:
        raw = pd.read_csv(path)
    return prepare(raw)


def _best_covariate(frame: pd.DataFrame, metric: str) -> str | None:
    """Pick the pre-randomisation feature most correlated with the outcome.

    CUPED stays unbiased for any pre-treatment covariate, so choosing the most
    correlated one only improves variance reduction; it does not bias the effect.
    Returns ``None`` when no usable feature column is present.
    """
    features = [c for c in FEATURE_COLUMNS if c in frame.columns]
    if not features:
        return None
    outcome = frame[metric].astype(float)
    best: tuple[float, str] | None = None
    for column in features:
        series = frame[column]
        if series.nunique(dropna=True) < 2:
            continue
        corr = abs(outcome.corr(series))
        if pd.isna(corr):
            continue
        if best is None or corr > best[0]:
            best = (corr, column)
    return best[1] if best else None


def experiment_readout(
    frame: pd.DataFrame,
    *,
    metric: str = "conversion",
    covariate: str = "auto",
) -> CriteoReadout:
    """Run the platform's own A/B machinery on the real treatment / control split."""
    if metric not in frame.columns:
        raise KeyError(f"outcome '{metric}' is not in the frame")
    chosen = _best_covariate(frame, metric) if covariate == "auto" else covariate
    if chosen is None or chosen not in frame.columns:
        raise ValueError("no usable pre-treatment covariate available for CUPED")

    return CriteoReadout(
        metric=metric,
        covariate=chosen,
        naive=difference_in_means(frame, metric),
        cuped=cuped_adjusted_effect(frame, metric, chosen),
        srm=sample_ratio_mismatch(frame),
    )


def _effect_row(label: str, e: EffectEstimate) -> str:
    return (
        f"| {label} | {e.control_mean:.4f} | {e.treatment_mean:.4f} | {e.effect:+.4f} "
        f"| [{e.ci_low:+.4f}, {e.ci_high:+.4f}] | {e.p_value:.3g} |"
    )


def render_markdown(readout: CriteoReadout, *, records: int) -> str:
    naive = readout.naive
    cuped = readout.cuped.estimate
    lines = [
        "# Criteo Uplift - real randomised-experiment readout",
        "",
        "> **Ad-tech, not fintech, and no known ground-truth lift.** This shows the "
        "platform's own experiment estimators behaving correctly on a *real* "
        "randomised treatment/control split; it does **not** recover a true effect "
        "(that is the synthetic synthetic-control chapter's job). Magnitudes are "
        "illustrative of method.",
        "",
        f"- Records analysed: `{records:,}`",
        f"- Outcome: `{readout.metric}` | CUPED covariate: `{readout.covariate}` "
        "(anonymised pre-randomisation feature)",
        "",
        "## Sample-ratio mismatch (assignment validity)",
        "",
        f"- control `{readout.srm.counts.get('control', 0):,}` vs "
        f"treatment `{readout.srm.counts.get('treatment', 0):,}`",
        f"- chi-square `{readout.srm.chi_square:.3g}`, p `{readout.srm.p_value:.3g}` -> "
        f"{'passes' if readout.srm.passed else 'FAILS'}",
        "",
        "## Effect on the outcome",
        "",
        "| Estimator | Control | Treatment | Effect | 95% CI | p |",
        "| --- | ---: | ---: | ---: | :---: | ---: |",
        _effect_row("Welch diff-in-means", naive),
        _effect_row("CUPED-adjusted", cuped),
        "",
        f"- CUPED variance reduction: `{readout.cuped.variance_reduction:.1%}` "
        f"(theta `{readout.cuped.theta:.4g}`).",
        "",
        "_Real data (Criteo Uplift v2.1, Diemert et al. 2018), analysed with the same "
        "`src.experiments.analysis` estimators used on the synthetic platform._",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the platform's A/B estimators on the real Criteo Uplift dataset."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to criteo-uplift-v2.1.csv (comma-separated).",
    )
    parser.add_argument("--metric", default="conversion", choices=OUTCOME_COLUMNS)
    parser.add_argument("--covariate", default="auto", help="'auto' or an f0..f11 column.")
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=1_000_000,
        help="Read only the first N rows (default 1,000,000; use 0 for the full file).",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    sample_rows = None if args.sample_rows in (0, None) else args.sample_rows
    frame = load_criteo(args.csv, sample_rows=sample_rows)
    readout = experiment_readout(frame, metric=args.metric, covariate=args.covariate)
    report = render_markdown(readout, records=len(frame))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote real-data readout to {args.output.resolve()}")
    else:
        print(report)


if __name__ == "__main__":
    main()
