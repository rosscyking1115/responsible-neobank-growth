"""Measure the synthetic population against public benchmark anchors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.calibration.benchmarks import PUBLIC_BENCHMARKS, Benchmark


@dataclass(frozen=True)
class CalibrationResult:
    metric: str
    label: str
    observed: float
    target: float
    tolerance: float
    deviation: float
    within: bool
    source: str
    note: str


def measure_synthetic(customer_outcomes: pd.DataFrame) -> dict[str, float]:
    """Observed population shares for each benchmark metric.

    Expects a customer-level frame (e.g. ``fct_customer_outcomes``) carrying the
    wellbeing/inclusion proxy columns. Missing columns are simply omitted.
    """
    observed: dict[str, float] = {}
    if customer_outcomes.empty:
        return observed

    if "new_to_uk_proxy" in customer_outcomes.columns:
        observed["new_to_uk_share"] = float(
            customer_outcomes["new_to_uk_proxy"].astype(bool).mean()
        )
    if "accessibility_need_proxy" in customer_outcomes.columns:
        observed["accessibility_need_share"] = float(
            customer_outcomes["accessibility_need_proxy"].astype(bool).mean()
        )
    if "digital_confidence_band" in customer_outcomes.columns:
        observed["low_digital_confidence_share"] = float(
            (customer_outcomes["digital_confidence_band"] == "low").mean()
        )
    return observed


def calibrate(
    customer_outcomes: pd.DataFrame,
    benchmarks: list[Benchmark] = PUBLIC_BENCHMARKS,
) -> list[CalibrationResult]:
    """Compare observed synthetic shares to each benchmark anchor."""
    observed = measure_synthetic(customer_outcomes)
    results: list[CalibrationResult] = []
    for benchmark in benchmarks:
        if benchmark.metric not in observed:
            continue
        value = observed[benchmark.metric]
        deviation = value - benchmark.target
        results.append(
            CalibrationResult(
                metric=benchmark.metric,
                label=benchmark.label,
                observed=round(value, 4),
                target=benchmark.target,
                tolerance=benchmark.tolerance,
                deviation=round(deviation, 4),
                within=abs(deviation) <= benchmark.tolerance,
                source=benchmark.source,
                note=benchmark.note,
            )
        )
    return results


def render_markdown(results: list[CalibrationResult]) -> str:
    lines = [
        "# Public-Data Calibration",
        "",
        "> Benchmark targets are **approximate, illustrative anchors** from public "
        "sources and must be verified against the cited source before real-world use.",
        "",
        "| Metric | Observed | Benchmark | Tolerance | Within? | Source |",
        "| --- | ---: | ---: | ---: | :---: | --- |",
    ]
    for r in results:
        flag = "yes" if r.within else "NO"
        lines.append(
            f"| {r.label} | {r.observed:.1%} | {r.target:.1%} | "
            f"+/-{r.tolerance:.1%} | {flag} | {r.source} |"
        )
    off = [r for r in results if not r.within]
    lines.extend(["", "## Notes", ""])
    if off:
        lines.append("Metrics outside tolerance (tune the generator or update the anchor):")
        lines.extend(
            f"- {r.label}: observed {r.observed:.1%} vs benchmark {r.target:.1%} "
            f"({r.deviation:+.1%})."
            for r in off
        )
    else:
        lines.append("All measured metrics are within benchmark tolerance.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Calibrate synthetic data to public anchors.")
    parser.add_argument("--db", type=Path, default=Path("neobank.duckdb"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    from app.dashboard_data import load_dashboard_data

    data = load_dashboard_data(args.db)
    results = calibrate(data.customer_outcomes)
    report = render_markdown(results)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote calibration report to {args.output.resolve()}")
    else:
        print(report)


if __name__ == "__main__":
    main()
