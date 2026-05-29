from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb

from src.monitoring.snapshot import (
    build_monitoring_snapshot,
    render_markdown,
    write_monitoring_snapshot,
)


def _build_monitoring_fixture(db_path: Path) -> None:
    with duckdb.connect(str(db_path)) as con:
        con.execute("create schema main_marts")
        con.execute(
            """
            create table main_marts.fct_activation as
            select *
            from (
                values
                    (1, date '2025-06-01', true),
                    (2, date '2025-06-02', false),
                    (3, date '2025-06-03', true),
                    (4, date '2025-06-04', false)
            ) as t(user_id, signup_date, activated_d7)
            """
        )
        con.execute(
            """
            create table main_marts.fct_experiment_user_metrics as
            select *
            from (
                values
                    (1, 0, 0, 0),
                    (2, 0, 0, 0),
                    (3, 0, 0, 0),
                    (4, 0, 0, 0)
            ) as t(user_id, support_contacts, complaints, app_crashes)
            """
        )
        con.execute(
            """
            create table main_marts.fct_pricing_outcomes as
            select *
            from (
                values
                    (10, 12.0, 1, 0.010),
                    (5, 3.0, 1, 0.000)
            ) as t(
                exposures,
                net_margin_30d_gbp,
                human_review_required_exposures,
                complaint_rate_14d
            )
            """
        )
        con.execute(
            """
            create table main_marts.mart_pricing_recommendations as
            select *
            from (
                values
                    ('scale', 10),
                    ('human_review', 5)
            ) as t(recommended_action, exposures)
            """
        )


def test_monitoring_snapshot_passes_for_healthy_fixture(tmp_path: Path) -> None:
    db_path = tmp_path / "monitoring.duckdb"
    batch_dir = tmp_path / "scores" / "score_date=2025-06-30"
    batch_dir.mkdir(parents=True)
    (batch_dir / "customer_scores_daily.parquet").write_text("scores", encoding="utf-8")
    _build_monitoring_fixture(db_path)

    snapshot = build_monitoring_snapshot(
        db_path=db_path,
        batch_score_dir=tmp_path / "scores",
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )
    markdown = render_markdown(snapshot)

    assert snapshot.overall_status == "pass"
    assert {check.name for check in snapshot.checks} >= {
        "duckdb_database",
        "required_marts",
        "activation_rate",
        "pricing_unit_economics",
        "activation_batch_scores",
        "api_contract_files",
    }
    assert "Monitoring Snapshot" in markdown


def test_monitoring_snapshot_flags_missing_database(tmp_path: Path) -> None:
    snapshot = build_monitoring_snapshot(
        db_path=tmp_path / "missing.duckdb",
        batch_score_dir=tmp_path / "scores",
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )

    assert snapshot.overall_status == "fail"
    assert snapshot.checks[0].name == "duckdb_database"
    assert snapshot.checks[0].status == "fail"


def test_write_monitoring_snapshot_outputs_json_and_markdown(tmp_path: Path) -> None:
    db_path = tmp_path / "monitoring.duckdb"
    _build_monitoring_fixture(db_path)
    snapshot = build_monitoring_snapshot(
        db_path=db_path,
        batch_score_dir=tmp_path / "scores",
        generated_at=datetime(2025, 6, 30, tzinfo=UTC),
    )

    result = write_monitoring_snapshot(
        snapshot=snapshot,
        output_dir=tmp_path / "monitoring",
    )

    assert result.json_path.exists()
    assert result.markdown_path.exists()
    assert result.json_path.parent.name == "snapshot_date=2025-06-30"
