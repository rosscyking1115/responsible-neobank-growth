from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.monitoring.model_report import (
    build_activation_model_monitoring_report,
    render_markdown,
    write_activation_model_monitoring_report,
)


def _score_frame(*, shift: float = 0.0, rows: int = 200) -> pd.DataFrame:
    probabilities = np.linspace(0.12 + shift, 0.72 + shift, rows).clip(0.01, 0.99)
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
            "income_segment": np.resize(["student", "middle", "high"], rows),
            "signup_channel": np.resize(["organic_search", "paid_social"], rows),
            "region": np.resize(["London", "Wales"], rows),
        }
    )


def _write_scores(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def test_model_monitoring_report_passes_with_reference(tmp_path: Path) -> None:
    score_path = tmp_path / "scores" / "score_date=2025-06-30" / "customer_scores_daily.parquet"
    reference_path = (
        tmp_path / "scores" / "score_date=2025-06-23" / "customer_scores_daily.parquet"
    )
    _write_scores(score_path, _score_frame())
    _write_scores(reference_path, _score_frame(shift=0.005))

    report = build_activation_model_monitoring_report(
        score_path=score_path,
        reference_score_path=reference_path,
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )
    markdown = render_markdown(report)

    assert report.overall_status == "pass"
    assert report.rows == 200
    assert report.model_version == "activation-test"
    assert report.distribution["p50"] > 0
    assert "Activation Model Monitoring Report" in markdown


def test_model_monitoring_report_warns_without_reference(tmp_path: Path) -> None:
    score_path = tmp_path / "scores" / "score_date=2025-06-30" / "customer_scores_daily.parquet"
    _write_scores(score_path, _score_frame())

    report = build_activation_model_monitoring_report(
        score_path=score_path,
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )

    drift_check = next(check for check in report.checks if check.name == "score_distribution_drift")
    assert report.overall_status == "warn"
    assert drift_check.status == "warn"


def test_model_monitoring_report_fails_when_scores_missing(tmp_path: Path) -> None:
    report = build_activation_model_monitoring_report(
        score_dir=tmp_path / "missing",
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )

    assert report.overall_status == "fail"
    assert report.rows == 0
    assert report.checks[0].name == "score_extract_available"


def test_write_model_monitoring_report_outputs_json_and_markdown(tmp_path: Path) -> None:
    score_path = tmp_path / "scores" / "score_date=2025-06-30" / "customer_scores_daily.parquet"
    _write_scores(score_path, _score_frame())
    report = build_activation_model_monitoring_report(
        score_path=score_path,
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )

    result = write_activation_model_monitoring_report(
        report=report,
        output_dir=tmp_path / "monitoring",
    )

    assert result.json_path.exists()
    assert result.markdown_path.exists()
    assert result.json_path.parent.name == "report_date=2025-06-30"
