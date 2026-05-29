from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from src.pricing.scenario_runs import (
    build_pricing_scenario_run,
    load_segment_priors,
    render_markdown,
    write_pricing_scenario_run,
)


def test_pricing_scenario_run_builds_portfolio_grid(tmp_path: Path) -> None:
    run = build_pricing_scenario_run(
        db_path=tmp_path / "missing.duckdb",
        incentives=[0.0, 4.0],
        run_date=date(2025, 6, 30),
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )
    markdown = render_markdown(run)

    assert run.run_date == "2025-06-30"
    assert len(run.scenarios) == 10
    assert len(run.sensitivity_rows) == 40
    assert run.executive_summary["scenario_count"] == 10
    assert "Pricing Scenario Run" in markdown


def test_pricing_scenario_run_writes_all_artifacts(tmp_path: Path) -> None:
    run = build_pricing_scenario_run(
        db_path=tmp_path / "missing.duckdb",
        incentives=[2.0],
        run_date=date(2025, 6, 30),
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )

    result = write_pricing_scenario_run(run=run, output_dir=tmp_path / "pricing")

    assert result.json_path.exists()
    assert result.markdown_path.exists()
    assert result.scenario_csv_path.exists()
    assert result.sensitivity_csv_path.exists()
    scenarios = pd.read_csv(result.scenario_csv_path)
    sensitivity = pd.read_csv(result.sensitivity_csv_path)
    assert len(scenarios) == 5
    assert len(sensitivity) == 20
    assert {"scenario_id", "expected_monthly_margin_gbp", "recommendation"}.issubset(
        scenarios.columns
    )


def test_segment_priors_fall_back_when_duckdb_missing(tmp_path: Path) -> None:
    priors = load_segment_priors(tmp_path / "missing.duckdb")

    assert {prior.segment for prior in priors} == {"student", "low", "middle", "high", "affluent"}
    assert all(prior.source == "fallback" for prior in priors)
