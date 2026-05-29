"""Generate activation score distribution and drift monitoring reports."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from src.modelling.batch_score_activation import DEFAULT_SCORE_OUTPUT_DIR

DEFAULT_MODEL_MONITORING_DIR = Path("artifacts/monitoring/model_activation")
SCORE_FILE_NAME = "customer_scores_daily.parquet"
Status = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class ModelMonitoringCheck:
    name: str
    status: Status
    value: str
    threshold: str
    message: str


@dataclass(frozen=True)
class ActivationModelMonitoringReport:
    generated_at: str
    score_path: str
    reference_score_path: str | None
    overall_status: Status
    rows: int
    model_version: str
    score_date: str
    checks: list[ModelMonitoringCheck]
    distribution: dict[str, float]
    segment_rows: list[dict[str, str | int | float]]


@dataclass(frozen=True)
class ModelMonitoringWriteResult:
    json_path: Path
    markdown_path: Path
    report: ActivationModelMonitoringReport


def _status(checks: list[ModelMonitoringCheck]) -> Status:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "warn" for check in checks):
        return "warn"
    return "pass"


def _latest_score_path(score_dir: Path) -> Path | None:
    score_paths = sorted(score_dir.glob(f"score_date=*/{SCORE_FILE_NAME}"))
    return score_paths[-1] if score_paths else None


def _load_scores(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    required_columns = {
        "score_date",
        "user_id",
        "model_version",
        "activation_probability",
        "activation_threshold",
        "decision",
        "vulnerable_customer_review",
        "income_segment",
        "signup_channel",
        "region",
    }
    missing = required_columns - set(frame.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Score file {path} is missing required columns: {missing_list}.")
    return frame


def _probability_distribution(scores: pd.Series) -> dict[str, float]:
    quantiles = scores.quantile([0.1, 0.25, 0.5, 0.75, 0.9])
    return {
        "mean": float(scores.mean()),
        "std": float(scores.std(ddof=0)),
        "p10": float(quantiles.loc[0.1]),
        "p25": float(quantiles.loc[0.25]),
        "p50": float(quantiles.loc[0.5]),
        "p75": float(quantiles.loc[0.75]),
        "p90": float(quantiles.loc[0.9]),
    }


def _psi(
    current_scores: pd.Series,
    reference_scores: pd.Series,
    *,
    buckets: int = 10,
) -> float:
    edges = np.linspace(0.0, 1.0, buckets + 1)
    current_counts, _ = np.histogram(current_scores, bins=edges)
    reference_counts, _ = np.histogram(reference_scores, bins=edges)
    current_pct = np.maximum(current_counts / max(current_counts.sum(), 1), 1e-6)
    reference_pct = np.maximum(reference_counts / max(reference_counts.sum(), 1), 1e-6)
    return float(np.sum((current_pct - reference_pct) * np.log(current_pct / reference_pct)))


def _segment_summary(scores: pd.DataFrame) -> list[dict[str, str | int | float]]:
    grouped = (
        scores.groupby("income_segment", as_index=False)
        .agg(
            rows=("user_id", "count"),
            mean_score=("activation_probability", "mean"),
            target_rate=("decision", lambda values: float((values == "target").mean())),
            vulnerable_review_rate=(
                "vulnerable_customer_review",
                lambda values: float(values.astype(bool).mean()),
            ),
        )
        .sort_values("rows", ascending=False)
    )
    return [
        {
            "income_segment": str(row.income_segment),
            "rows": int(row.rows),
            "mean_score": round(float(row.mean_score), 6),
            "target_rate": round(float(row.target_rate), 6),
            "vulnerable_review_rate": round(float(row.vulnerable_review_rate), 6),
        }
        for row in grouped.itertuples(index=False)
    ]


def _score_date(scores: pd.DataFrame) -> str:
    return pd.to_datetime(scores["score_date"]).max().date().isoformat()


def _model_version(scores: pd.DataFrame) -> str:
    versions = sorted(scores["model_version"].astype(str).unique())
    return versions[0] if len(versions) == 1 else "multiple"


def _checks(
    scores: pd.DataFrame,
    *,
    score_path: Path,
    reference_score_path: Path | None,
    reference_scores: pd.DataFrame | None,
) -> list[ModelMonitoringCheck]:
    probability = scores["activation_probability"].astype(float)
    target_rate = float((scores["decision"] == "target").mean())
    vulnerable_review_rate = float(scores["vulnerable_customer_review"].astype(bool).mean())
    threshold = float(scores["activation_threshold"].astype(float).median())
    checks = [
        ModelMonitoringCheck(
            name="score_extract_available",
            status="pass",
            value=str(score_path),
            threshold="readable parquet score extract",
            message="Activation score extract is readable.",
        ),
        ModelMonitoringCheck(
            name="score_row_count",
            status="pass" if len(scores) >= 100 else "warn",
            value=f"{len(scores):,}",
            threshold=">= 100 rows",
            message="Score volume is large enough for distribution monitoring.",
        ),
        ModelMonitoringCheck(
            name="score_probability_bounds",
            status="pass" if probability.between(0, 1).all() else "fail",
            value=f"{probability.min():.4f} to {probability.max():.4f}",
            threshold="all probabilities between 0 and 1",
            message="Activation probabilities are within contract bounds.",
        ),
        ModelMonitoringCheck(
            name="targeting_rate",
            status="pass" if 0.01 <= target_rate <= 0.60 else "warn",
            value=f"{target_rate:.2%}",
            threshold="1% to 60%",
            message="Targeting rate remains within operational review bounds.",
        ),
        ModelMonitoringCheck(
            name="vulnerable_review_rate",
            status="pass" if vulnerable_review_rate <= 0.10 else "warn",
            value=f"{vulnerable_review_rate:.2%}",
            threshold="<= 10%",
            message="Vulnerable-customer manual-review load remains manageable.",
        ),
        ModelMonitoringCheck(
            name="activation_threshold",
            status="pass" if 0 <= threshold <= 1 else "fail",
            value=f"{threshold:.4f}",
            threshold="0 to 1",
            message="Model decision threshold is within probability bounds.",
        ),
    ]
    if reference_scores is None:
        checks.append(
            ModelMonitoringCheck(
                name="score_distribution_drift",
                status="warn",
                value="reference missing",
                threshold="reference score extract provided",
                message="No reference score extract was provided for PSI drift monitoring.",
            )
        )
    else:
        psi = _psi(probability, reference_scores["activation_probability"].astype(float))
        checks.append(
            ModelMonitoringCheck(
                name="score_distribution_drift",
                status="pass" if psi <= 0.10 else "warn" if psi <= 0.25 else "fail",
                value=f"{psi:.4f}",
                threshold="PSI <= 0.10 pass, <= 0.25 warn",
                message=(
                    "Population stability index between current and reference "
                    f"scores from {reference_score_path}."
                ),
            )
        )
    return checks


def build_activation_model_monitoring_report(
    *,
    score_path: Path | None = None,
    score_dir: Path = DEFAULT_SCORE_OUTPUT_DIR,
    reference_score_path: Path | None = None,
    generated_at: datetime | None = None,
) -> ActivationModelMonitoringReport:
    effective_generated_at = generated_at or datetime.now(UTC)
    resolved_score_path = score_path or _latest_score_path(score_dir)
    if resolved_score_path is None or not resolved_score_path.exists():
        check = ModelMonitoringCheck(
            name="score_extract_available",
            status="fail",
            value=str(resolved_score_path or score_dir),
            threshold="latest customer_scores_daily.parquet exists",
            message="Activation score extract is missing.",
        )
        return ActivationModelMonitoringReport(
            generated_at=effective_generated_at.isoformat(),
            score_path=str(resolved_score_path or ""),
            reference_score_path=str(reference_score_path) if reference_score_path else None,
            overall_status="fail",
            rows=0,
            model_version="unknown",
            score_date="unknown",
            checks=[check],
            distribution={},
            segment_rows=[],
        )

    scores = _load_scores(resolved_score_path)
    reference_scores = None
    if reference_score_path and reference_score_path.exists():
        reference_scores = _load_scores(reference_score_path)
    checks = _checks(
        scores,
        score_path=resolved_score_path,
        reference_score_path=reference_score_path,
        reference_scores=reference_scores,
    )
    return ActivationModelMonitoringReport(
        generated_at=effective_generated_at.isoformat(),
        score_path=str(resolved_score_path),
        reference_score_path=str(reference_score_path) if reference_score_path else None,
        overall_status=_status(checks),
        rows=len(scores),
        model_version=_model_version(scores),
        score_date=_score_date(scores),
        checks=checks,
        distribution=_probability_distribution(scores["activation_probability"].astype(float)),
        segment_rows=_segment_summary(scores),
    )


def render_markdown(report: ActivationModelMonitoringReport) -> str:
    lines = [
        "# Activation Model Monitoring Report",
        "",
        f"- Generated at: `{report.generated_at}`",
        f"- Score date: `{report.score_date}`",
        f"- Model version: `{report.model_version}`",
        f"- Rows: `{report.rows:,}`",
        f"- Overall status: `{report.overall_status}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Value | Threshold |",
        "| --- | --- | --- | --- |",
    ]
    for check in report.checks:
        lines.append(f"| {check.name} | {check.status} | {check.value} | {check.threshold} |")
    if report.distribution:
        lines.extend(
            [
                "",
                "## Score Distribution",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
            ]
        )
        for metric, value in report.distribution.items():
            lines.append(f"| {metric} | {value:.4f} |")
    if report.segment_rows:
        lines.extend(
            [
                "",
                "## Segment Summary",
                "",
                "| Income segment | Rows | Mean score | Target rate | Vulnerable review rate |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in report.segment_rows:
            lines.append(
                "| "
                f"{row['income_segment']} | {row['rows']} | {row['mean_score']:.4f} | "
                f"{row['target_rate']:.2%} | {row['vulnerable_review_rate']:.2%} |"
            )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            *[f"- {check.name}: {check.message}" for check in report.checks],
            "",
        ]
    )
    return "\n".join(lines)


def write_activation_model_monitoring_report(
    *,
    report: ActivationModelMonitoringReport,
    output_dir: Path = DEFAULT_MODEL_MONITORING_DIR,
    report_date: date | None = None,
) -> ModelMonitoringWriteResult:
    effective_date = report_date or datetime.fromisoformat(report.generated_at).date()
    partition_dir = output_dir / f"report_date={effective_date.isoformat()}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    json_path = partition_dir / "activation_model_monitoring.json"
    markdown_path = partition_dir / "activation_model_monitoring.md"
    json_path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return ModelMonitoringWriteResult(
        json_path=json_path,
        markdown_path=markdown_path,
        report=report,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate activation model monitoring report.")
    parser.add_argument("--score-path", type=Path, default=None)
    parser.add_argument("--score-dir", type=Path, default=DEFAULT_SCORE_OUTPUT_DIR)
    parser.add_argument("--reference-score-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_MODEL_MONITORING_DIR)
    parser.add_argument("--report-date", type=date.fromisoformat, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_activation_model_monitoring_report(
        score_path=args.score_path,
        score_dir=args.score_dir,
        reference_score_path=args.reference_score_path,
    )
    result = write_activation_model_monitoring_report(
        report=report,
        output_dir=args.output_dir,
        report_date=args.report_date,
    )
    print(
        f"Wrote activation model monitoring report to {result.json_path} "
        f"and {result.markdown_path}; overall status={report.overall_status}."
    )


if __name__ == "__main__":
    main()
