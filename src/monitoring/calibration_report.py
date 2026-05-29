"""Generate realised-label calibration reports for activation scores."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import duckdb
import numpy as np
import pandas as pd

from src.modelling.batch_score_activation import DEFAULT_SCORE_OUTPUT_DIR
from src.monitoring.model_report import SCORE_FILE_NAME

DEFAULT_CALIBRATION_MONITORING_DIR = Path("artifacts/monitoring/model_activation_calibration")
Status = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class CalibrationCheck:
    name: str
    status: Status
    value: str
    threshold: str
    message: str


@dataclass(frozen=True)
class ActivationCalibrationReport:
    generated_at: str
    score_path: str
    label_source: str
    overall_status: Status
    rows: int
    model_version: str
    score_date: str
    metrics: dict[str, float]
    checks: list[CalibrationCheck]
    calibration_bins: list[dict[str, int | float]]
    segment_rows: list[dict[str, str | int | float]]


@dataclass(frozen=True)
class CalibrationWriteResult:
    json_path: Path
    markdown_path: Path
    report: ActivationCalibrationReport


def _status(checks: list[CalibrationCheck]) -> Status:
    statuses = [check.status for check in checks]
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    return "pass"


def _latest_score_path(score_dir: Path) -> Path | None:
    score_paths = sorted(score_dir.glob(f"score_date=*/{SCORE_FILE_NAME}"))
    return score_paths[-1] if score_paths else None


def _load_scores(path: Path) -> pd.DataFrame:
    scores = pd.read_parquet(path)
    required = {
        "score_date",
        "user_id",
        "model_version",
        "activation_probability",
        "income_segment",
        "signup_channel",
        "region",
    }
    missing = required.difference(scores.columns)
    if missing:
        raise ValueError(f"Score extract is missing required columns: {sorted(missing)}")
    return scores


def _load_labels_from_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        labels = pd.read_parquet(path)
    elif path.suffix.lower() == ".csv":
        labels = pd.read_csv(path)
    else:
        raise ValueError("Label path must be a parquet or csv file")
    return _prepare_labels(labels, str(path))


def _load_labels_from_duckdb(path: Path) -> pd.DataFrame:
    query = """
        select
            user_id,
            activated_d7
        from main_marts.fct_activation
    """
    with duckdb.connect(str(path), read_only=True) as con:
        labels = con.execute(query).fetchdf()
    return _prepare_labels(labels, str(path))


def _prepare_labels(labels: pd.DataFrame, source: str) -> pd.DataFrame:
    required = {"user_id", "activated_d7"}
    missing = required.difference(labels.columns)
    if missing:
        raise ValueError(f"Label source {source} is missing required columns: {sorted(missing)}")
    prepared = labels[["user_id", "activated_d7"]].copy()
    prepared["user_id"] = prepared["user_id"].astype(str)
    prepared["activated_d7"] = prepared["activated_d7"].astype(int)
    return prepared.drop_duplicates("user_id")


def _join_scores_and_labels(scores: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    prepared_scores = scores.copy()
    prepared_scores["user_id"] = prepared_scores["user_id"].astype(str)
    joined = prepared_scores.merge(labels, on="user_id", how="inner")
    joined["activation_probability"] = joined["activation_probability"].astype(float)
    joined["activated_d7"] = joined["activated_d7"].astype(int)
    return joined


def _expected_calibration_error(
    probabilities: pd.Series,
    labels: pd.Series,
    *,
    bins: int = 10,
) -> tuple[float, list[dict[str, int | float]]]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    bin_rows: list[dict[str, int | float]] = []
    ece = 0.0
    total = len(probabilities)
    for index in range(bins):
        lower = edges[index]
        upper = edges[index + 1]
        if index == bins - 1:
            mask = (probabilities >= lower) & (probabilities <= upper)
        else:
            mask = (probabilities >= lower) & (probabilities < upper)
        count = int(mask.sum())
        if count == 0:
            continue
        mean_prediction = float(probabilities[mask].mean())
        observed_rate = float(labels[mask].mean())
        absolute_gap = abs(mean_prediction - observed_rate)
        ece += (count / total) * absolute_gap
        bin_rows.append(
            {
                "bin": index + 1,
                "lower": round(float(lower), 4),
                "upper": round(float(upper), 4),
                "rows": count,
                "mean_prediction": round(mean_prediction, 6),
                "observed_rate": round(observed_rate, 6),
                "absolute_gap": round(absolute_gap, 6),
            }
        )
    return float(ece), bin_rows


def _metrics(joined: pd.DataFrame) -> tuple[dict[str, float], list[dict[str, int | float]]]:
    probabilities = joined["activation_probability"]
    labels = joined["activated_d7"]
    ece, bins = _expected_calibration_error(probabilities, labels)
    brier = float(np.mean(np.square(probabilities - labels)))
    mean_prediction = float(probabilities.mean())
    observed_rate = float(labels.mean())
    return (
        {
            "mean_prediction": round(mean_prediction, 6),
            "observed_rate": round(observed_rate, 6),
            "prediction_bias": round(mean_prediction - observed_rate, 6),
            "brier_score": round(brier, 6),
            "expected_calibration_error": round(ece, 6),
        },
        bins,
    )


def _segment_summary(
    joined: pd.DataFrame,
    *,
    min_rows: int = 30,
) -> list[dict[str, str | int | float]]:
    rows: list[dict[str, str | int | float]] = []
    for column in ["income_segment", "signup_channel", "region"]:
        summary = (
            joined.groupby(column, as_index=False)
            .agg(
                rows=("user_id", "count"),
                mean_prediction=("activation_probability", "mean"),
                observed_rate=("activated_d7", "mean"),
            )
            .sort_values("rows", ascending=False)
        )
        for row in summary.itertuples(index=False):
            gap = float(row.mean_prediction - row.observed_rate)
            rows.append(
                {
                    "segment_type": column,
                    "segment": str(getattr(row, column)),
                    "rows": int(row.rows),
                    "mean_prediction": round(float(row.mean_prediction), 6),
                    "observed_rate": round(float(row.observed_rate), 6),
                    "calibration_gap": round(gap, 6),
                    "included_in_gap_check": int(row.rows) >= min_rows,
                }
            )
    return rows


def _score_date(scores: pd.DataFrame) -> str:
    return pd.to_datetime(scores["score_date"]).max().date().isoformat()


def _model_version(scores: pd.DataFrame) -> str:
    versions = sorted(scores["model_version"].astype(str).unique())
    return versions[0] if len(versions) == 1 else "multiple"


def _check_level(value: float, pass_limit: float, warn_limit: float) -> Status:
    if value <= pass_limit:
        return "pass"
    if value <= warn_limit:
        return "warn"
    return "fail"


def _checks(
    joined: pd.DataFrame,
    metrics: dict[str, float],
    segment_rows: list[dict[str, str | int | float]],
    *,
    score_path: Path,
    label_source: str,
) -> list[CalibrationCheck]:
    eligible_segment_gaps = [
        abs(float(row["calibration_gap"]))
        for row in segment_rows
        if bool(row["included_in_gap_check"])
    ]
    max_segment_gap = max(eligible_segment_gaps, default=0.0)
    bias = abs(metrics["prediction_bias"])
    checks = [
        CalibrationCheck(
            name="realised_labels_available",
            status="pass",
            value=f"{len(joined):,}",
            threshold="at least one matched score and D7 label",
            message=f"Matched activation scores from {score_path} to labels from {label_source}.",
        ),
        CalibrationCheck(
            name="calibration_sample_size",
            status="pass" if len(joined) >= 100 else "warn",
            value=f"{len(joined):,}",
            threshold=">= 100 matched users",
            message="Matched sample is large enough for a lightweight calibration readout.",
        ),
        CalibrationCheck(
            name="expected_calibration_error",
            status=_check_level(metrics["expected_calibration_error"], 0.05, 0.08),
            value=f"{metrics['expected_calibration_error']:.2%}",
            threshold="pass <= 5%, warn <= 8%",
            message="Compares average predicted probability with observed activation by score bin.",
        ),
        CalibrationCheck(
            name="brier_score",
            status=_check_level(metrics["brier_score"], 0.25, 0.30),
            value=f"{metrics['brier_score']:.4f}",
            threshold="pass <= 0.25, warn <= 0.30",
            message="Measures realised probabilistic error against D7 activation labels.",
        ),
        CalibrationCheck(
            name="prediction_bias",
            status=_check_level(bias, 0.03, 0.06),
            value=f"{metrics['prediction_bias']:.2%}",
            threshold="absolute bias pass <= 3 pp, warn <= 6 pp",
            message="Compares portfolio mean score with realised activation rate.",
        ),
        CalibrationCheck(
            name="segment_calibration_gap",
            status=_check_level(max_segment_gap, 0.08, 0.12),
            value=f"{max_segment_gap:.2%}",
            threshold="largest segment gap pass <= 8 pp, warn <= 12 pp",
            message="Largest absolute calibration gap across income, channel, and region segments.",
        ),
    ]
    return checks


def _missing_report(
    *,
    score_path: Path | None,
    label_source: str,
    generated_at: datetime,
    message: str,
) -> ActivationCalibrationReport:
    check = CalibrationCheck(
        name="realised_labels_available",
        status="fail",
        value=str(score_path or label_source),
        threshold="score extract and D7 labels can be joined",
        message=message,
    )
    return ActivationCalibrationReport(
        generated_at=generated_at.isoformat(),
        score_path=str(score_path or ""),
        label_source=label_source,
        overall_status="fail",
        rows=0,
        model_version="unknown",
        score_date="unknown",
        metrics={},
        checks=[check],
        calibration_bins=[],
        segment_rows=[],
    )


def build_activation_calibration_report(
    *,
    score_path: Path | None = None,
    score_dir: Path = DEFAULT_SCORE_OUTPUT_DIR,
    label_path: Path | None = None,
    db_path: Path | None = None,
    generated_at: datetime | None = None,
) -> ActivationCalibrationReport:
    generated_at = generated_at or datetime.now(UTC)
    resolved_score_path = score_path or _latest_score_path(score_dir)
    if resolved_score_path is None or not resolved_score_path.exists():
        return _missing_report(
            score_path=resolved_score_path,
            label_source=str(label_path or db_path or "missing labels"),
            generated_at=generated_at,
            message="Activation score extract is missing.",
        )

    label_source = str(label_path or db_path or "")
    if not label_path and not db_path:
        return _missing_report(
            score_path=resolved_score_path,
            label_source="missing labels",
            generated_at=generated_at,
            message="Provide --label-path or --db after D7 outcomes have matured.",
        )

    scores = _load_scores(resolved_score_path)
    labels = _load_labels_from_file(label_path) if label_path else _load_labels_from_duckdb(db_path)
    joined = _join_scores_and_labels(scores, labels)
    if joined.empty:
        return _missing_report(
            score_path=resolved_score_path,
            label_source=label_source,
            generated_at=generated_at,
            message="No activation scores matched realised D7 labels.",
        )

    metrics, calibration_bins = _metrics(joined)
    segment_rows = _segment_summary(joined)
    checks = _checks(
        joined,
        metrics,
        segment_rows,
        score_path=resolved_score_path,
        label_source=label_source,
    )
    return ActivationCalibrationReport(
        generated_at=generated_at.isoformat(),
        score_path=str(resolved_score_path),
        label_source=label_source,
        overall_status=_status(checks),
        rows=len(joined),
        model_version=_model_version(scores),
        score_date=_score_date(scores),
        metrics=metrics,
        checks=checks,
        calibration_bins=calibration_bins,
        segment_rows=segment_rows,
    )


def render_markdown(report: ActivationCalibrationReport) -> str:
    check_rows = "\n".join(
        "| "
        f"{check.name} | {check.status} | {check.value} | {check.threshold} | "
        f"{check.message} |"
        for check in report.checks
    )
    bin_rows = "\n".join(
        "| "
        f"{row['bin']} | {row['rows']} | {row['mean_prediction']:.4f} | "
        f"{row['observed_rate']:.4f} | {row['absolute_gap']:.4f} |"
        for row in report.calibration_bins
    )
    segment_rows = "\n".join(
        "| "
        f"{row['segment_type']} | {row['segment']} | {row['rows']} | "
        f"{row['mean_prediction']:.4f} | {row['observed_rate']:.4f} | "
        f"{row['calibration_gap']:.4f} |"
        for row in report.segment_rows
    )
    metrics_rows = "\n".join(
        f"- {name}: {value:.4f}" for name, value in report.metrics.items()
    ) or "- No metrics available."
    return f"""# Activation Calibration Monitoring Report

- Generated at: `{report.generated_at}`
- Overall status: `{report.overall_status}`
- Score date: `{report.score_date}`
- Model version: `{report.model_version}`
- Matched rows: `{report.rows:,}`
- Score path: `{report.score_path}`
- Label source: `{report.label_source}`

## Metrics

{metrics_rows}

## Checks

| Check | Status | Value | Threshold | Message |
| --- | --- | --- | --- | --- |
{check_rows}

## Calibration Bins

| Bin | Rows | Mean prediction | Observed rate | Absolute gap |
| --- | ---: | ---: | ---: | ---: |
{bin_rows}

## Segment Calibration

| Segment type | Segment | Rows | Mean prediction | Observed rate | Calibration gap |
| --- | --- | ---: | ---: | ---: | ---: |
{segment_rows}
"""


def write_activation_calibration_report(
    *,
    report: ActivationCalibrationReport,
    output_dir: Path = DEFAULT_CALIBRATION_MONITORING_DIR,
) -> CalibrationWriteResult:
    report_date = datetime.fromisoformat(report.generated_at).date()
    partition_dir = output_dir / f"report_date={report_date.isoformat()}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    json_path = partition_dir / "activation_calibration_monitoring.json"
    markdown_path = partition_dir / "activation_calibration_monitoring.md"
    json_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return CalibrationWriteResult(
        json_path=json_path,
        markdown_path=markdown_path,
        report=report,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate activation calibration monitoring report."
    )
    parser.add_argument("--score-path", type=Path, default=None)
    parser.add_argument("--score-dir", type=Path, default=DEFAULT_SCORE_OUTPUT_DIR)
    parser.add_argument("--label-path", type=Path, default=None)
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_CALIBRATION_MONITORING_DIR)
    parser.add_argument("--report-date", type=date.fromisoformat, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generated_at = (
        datetime.combine(args.report_date, datetime.min.time(), tzinfo=UTC)
        if args.report_date
        else None
    )
    report = build_activation_calibration_report(
        score_path=args.score_path,
        score_dir=args.score_dir,
        label_path=args.label_path,
        db_path=args.db,
        generated_at=generated_at,
    )
    result = write_activation_calibration_report(report=report, output_dir=args.output_dir)
    print(
        f"Wrote activation calibration monitoring report to {result.json_path} "
        f"and {result.markdown_path}; status={result.report.overall_status}."
    )


if __name__ == "__main__":
    main()
