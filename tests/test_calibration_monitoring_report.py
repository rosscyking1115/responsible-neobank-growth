from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.monitoring.calibration_report import (
    build_activation_calibration_report,
    render_markdown,
    write_activation_calibration_report,
)


def _score_frame(*, rows: int = 200, overconfident: bool = False) -> pd.DataFrame:
    probabilities = np.repeat([0.25, 0.75], rows // 2)
    if overconfident:
        probabilities = np.repeat([0.05, 0.95], rows // 2)
    return pd.DataFrame(
        {
            "score_date": pd.to_datetime(["2025-06-30"] * rows),
            "user_id": [f"user_{index:04d}" for index in range(rows)],
            "signup_date": pd.to_datetime(["2025-01-01"] * rows),
            "model_version": "activation-test",
            "activation_probability": probabilities,
            "activation_threshold": 0.35,
            "decision": np.where(probabilities <= 0.35, "target", "monitor"),
            "vulnerable_customer_review": [False] * rows,
            "income_segment": ["middle"] * rows,
            "signup_channel": ["organic_search"] * rows,
            "region": ["London"] * rows,
        }
    )


def _label_frame(*, rows: int = 200) -> pd.DataFrame:
    labels = np.concatenate(
        [
            np.resize([1, 0, 0, 0], rows // 2),
            np.resize([1, 1, 1, 0], rows // 2),
        ]
    )
    return pd.DataFrame(
        {
            "user_id": [f"user_{index:04d}" for index in range(rows)],
            "activated_d7": labels,
        }
    )


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def test_calibration_report_passes_with_realised_labels(tmp_path: Path) -> None:
    score_path = tmp_path / "scores" / "score_date=2025-06-30" / "customer_scores_daily.parquet"
    label_path = tmp_path / "labels.parquet"
    _write_parquet(score_path, _score_frame())
    _write_parquet(label_path, _label_frame())

    report = build_activation_calibration_report(
        score_path=score_path,
        label_path=label_path,
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )
    markdown = render_markdown(report)

    assert report.overall_status == "pass"
    assert report.rows == 200
    assert report.metrics["expected_calibration_error"] == 0
    assert "Activation Calibration Monitoring Report" in markdown


def test_calibration_report_warns_or_fails_when_model_is_miscalibrated(tmp_path: Path) -> None:
    score_path = tmp_path / "scores" / "score_date=2025-06-30" / "customer_scores_daily.parquet"
    label_path = tmp_path / "labels.parquet"
    _write_parquet(score_path, _score_frame(overconfident=True))
    _write_parquet(label_path, _label_frame())

    report = build_activation_calibration_report(
        score_path=score_path,
        label_path=label_path,
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )

    calibration_check = next(
        check for check in report.checks if check.name == "expected_calibration_error"
    )
    assert report.overall_status == "fail"
    assert calibration_check.status == "fail"


def test_calibration_report_fails_without_labels(tmp_path: Path) -> None:
    score_path = tmp_path / "scores" / "score_date=2025-06-30" / "customer_scores_daily.parquet"
    _write_parquet(score_path, _score_frame())

    report = build_activation_calibration_report(
        score_path=score_path,
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )

    assert report.overall_status == "fail"
    assert report.rows == 0
    assert report.checks[0].name == "realised_labels_available"


def test_write_calibration_report_outputs_json_and_markdown(tmp_path: Path) -> None:
    score_path = tmp_path / "scores" / "score_date=2025-06-30" / "customer_scores_daily.parquet"
    label_path = tmp_path / "labels.parquet"
    _write_parquet(score_path, _score_frame())
    _write_parquet(label_path, _label_frame())
    report = build_activation_calibration_report(
        score_path=score_path,
        label_path=label_path,
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )

    result = write_activation_calibration_report(
        report=report,
        output_dir=tmp_path / "monitoring",
    )

    assert result.json_path.exists()
    assert result.markdown_path.exists()
    assert result.json_path.parent.name == "report_date=2025-06-30"
