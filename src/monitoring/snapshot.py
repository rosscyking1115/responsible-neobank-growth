"""Generate a compact monitoring snapshot for the local DuckDB data product."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import duckdb

DEFAULT_DB_PATH = Path("neobank.duckdb")
DEFAULT_OUTPUT_DIR = Path("artifacts/monitoring")
DEFAULT_BATCH_SCORE_DIR = Path("artifacts/scoring/activation")
REQUIRED_MARTS = [
    "fct_activation",
    "fct_experiment_user_metrics",
    "fct_pricing_outcomes",
    "mart_pricing_recommendations",
]

Status = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class MonitoringCheck:
    name: str
    status: Status
    value: str
    threshold: str
    message: str


@dataclass(frozen=True)
class MonitoringSnapshot:
    generated_at: str
    db_path: str
    overall_status: Status
    checks: list[MonitoringCheck]


@dataclass(frozen=True)
class SnapshotWriteResult:
    json_path: Path
    markdown_path: Path
    snapshot: MonitoringSnapshot


def _status(checks: list[MonitoringCheck]) -> Status:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "warn" for check in checks):
        return "warn"
    return "pass"


def _table_exists(con: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = con.execute(
        """
        select count(*) > 0
        from information_schema.tables
        where table_schema = 'main_marts'
          and table_name = ?
        """,
        [table_name],
    ).fetchone()
    return bool(row[0]) if row else False


def _fetch_one(con: duckdb.DuckDBPyConnection, query: str) -> tuple | None:
    return con.execute(query).fetchone()


def _availability_checks(
    con: duckdb.DuckDBPyConnection,
    *,
    db_path: Path,
) -> list[MonitoringCheck]:
    checks = [
        MonitoringCheck(
            name="duckdb_database",
            status="pass",
            value=str(db_path),
            threshold="database file exists and opens read-only",
            message="DuckDB metrics layer is available.",
        )
    ]
    missing = [table for table in REQUIRED_MARTS if not _table_exists(con, table)]
    checks.append(
        MonitoringCheck(
            name="required_marts",
            status="fail" if missing else "pass",
            value=", ".join(missing) if missing else "all present",
            threshold=", ".join(REQUIRED_MARTS),
            message="Required mart tables for dashboard, pricing, and monitoring.",
        )
    )
    return checks


def _activation_checks(con: duckdb.DuckDBPyConnection) -> list[MonitoringCheck]:
    if not _table_exists(con, "fct_activation"):
        return []
    users, activation_rate, latest_signup = _fetch_one(
        con,
        """
        select
            count(*) as users,
            avg(case when activated_d7 then 1.0 else 0.0 end) as activation_rate,
            max(signup_date) as latest_signup
        from main_marts.fct_activation
        """,
    )
    activation_rate = float(activation_rate or 0)
    checks = [
        MonitoringCheck(
            name="activation_rate",
            status="pass" if 0.25 <= activation_rate <= 0.75 else "warn",
            value=f"{activation_rate:.2%}",
            threshold="25% to 75%",
            message=f"D7 activation rate across {int(users):,} users.",
        ),
        MonitoringCheck(
            name="activation_source_freshness",
            status="pass" if latest_signup is not None else "fail",
            value=str(latest_signup),
            threshold="latest signup date is populated",
            message="Freshness proxy for the activation mart.",
        ),
    ]
    return checks


def _experiment_guardrail_checks(con: duckdb.DuckDBPyConnection) -> list[MonitoringCheck]:
    if not _table_exists(con, "fct_experiment_user_metrics"):
        return []
    support_rate, complaint_rate, crash_rate = _fetch_one(
        con,
        """
        select
            avg(case when support_contacts > 0 then 1.0 else 0.0 end),
            avg(case when complaints > 0 then 1.0 else 0.0 end),
            avg(case when app_crashes > 0 then 1.0 else 0.0 end)
        from main_marts.fct_experiment_user_metrics
        """,
    )
    support_rate = float(support_rate or 0)
    complaint_rate = float(complaint_rate or 0)
    crash_rate = float(crash_rate or 0)
    return [
        MonitoringCheck(
            name="experiment_support_contact_rate",
            status="pass" if support_rate <= 0.20 else "warn",
            value=f"{support_rate:.2%}",
            threshold="<= 20%",
            message="Support-load guardrail across experiment users.",
        ),
        MonitoringCheck(
            name="experiment_complaint_rate",
            status="pass" if complaint_rate <= 0.05 else "fail",
            value=f"{complaint_rate:.2%}",
            threshold="<= 5%",
            message="Complaint guardrail across experiment users.",
        ),
        MonitoringCheck(
            name="experiment_app_crash_rate",
            status="pass" if crash_rate <= 0.10 else "warn",
            value=f"{crash_rate:.2%}",
            threshold="<= 10%",
            message="App stability guardrail across experiment users.",
        ),
    ]


def _pricing_checks(con: duckdb.DuckDBPyConnection) -> list[MonitoringCheck]:
    if not _table_exists(con, "fct_pricing_outcomes"):
        return []
    row = _fetch_one(
        con,
        """
        select
            sum(exposures),
            sum(net_margin_30d_gbp),
            sum(human_review_required_exposures)::double / nullif(sum(exposures), 0),
            sum(complaint_rate_14d * exposures)::double / nullif(sum(exposures), 0)
        from main_marts.fct_pricing_outcomes
        """,
    )
    exposures, net_margin, human_review_rate, complaint_rate = row
    exposures = int(exposures or 0)
    net_margin = float(net_margin or 0)
    human_review_rate = float(human_review_rate or 0)
    complaint_rate = float(complaint_rate or 0)
    return [
        MonitoringCheck(
            name="pricing_exposure_coverage",
            status="pass" if exposures > 0 else "fail",
            value=f"{exposures:,}",
            threshold="> 0 exposures",
            message="Pricing mart has offer exposure coverage.",
        ),
        MonitoringCheck(
            name="pricing_unit_economics",
            status="pass" if net_margin >= 0 else "warn",
            value=f"GBP {net_margin:,.0f}",
            threshold=">= GBP 0 net margin",
            message="Thirty-day pricing margin after incentive cost.",
        ),
        MonitoringCheck(
            name="pricing_human_review_rate",
            status="pass" if human_review_rate <= 0.25 else "warn",
            value=f"{human_review_rate:.2%}",
            threshold="<= 25%",
            message="Human-review load for pricing recommendations.",
        ),
        MonitoringCheck(
            name="pricing_complaint_rate",
            status="pass" if complaint_rate <= 0.025 else "fail",
            value=f"{complaint_rate:.2%}",
            threshold="<= 2.5%",
            message="Complaint guardrail for pricing recommendations.",
        ),
    ]


def _pricing_recommendation_checks(con: duckdb.DuckDBPyConnection) -> list[MonitoringCheck]:
    if not _table_exists(con, "mart_pricing_recommendations"):
        return []
    total_rows, actionable_rows = _fetch_one(
        con,
        """
        select
            count(*),
            sum(case when recommended_action in ('scale', 'test', 'human_review') then 1 else 0 end)
        from main_marts.mart_pricing_recommendations
        """,
    )
    total_rows = int(total_rows or 0)
    actionable_rows = int(actionable_rows or 0)
    return [
        MonitoringCheck(
            name="pricing_recommendation_coverage",
            status="pass" if total_rows > 0 and actionable_rows > 0 else "fail",
            value=f"{actionable_rows:,}/{total_rows:,}",
            threshold="at least one actionable recommendation",
            message="Pricing recommendation mart has usable decision rows.",
        )
    ]


def _batch_scoring_check(batch_score_dir: Path) -> MonitoringCheck:
    score_files = sorted(batch_score_dir.glob("score_date=*/customer_scores_daily.parquet"))
    if not score_files:
        return MonitoringCheck(
            name="activation_batch_scores",
            status="warn",
            value="missing",
            threshold="latest customer_scores_daily.parquet exists",
            message="Activation batch scores have not been generated locally.",
        )
    latest = score_files[-1]
    return MonitoringCheck(
        name="activation_batch_scores",
        status="pass" if latest.stat().st_size > 0 else "fail",
        value=str(latest),
        threshold="latest customer_scores_daily.parquet is non-empty",
        message="Latest activation batch score extract is available.",
    )


def _api_contract_check() -> MonitoringCheck:
    required_paths = [Path("api/main.py"), Path("api/schemas.py"), Path("docs/API.md")]
    missing = [str(path) for path in required_paths if not path.exists()]
    return MonitoringCheck(
        name="api_contract_files",
        status="fail" if missing else "pass",
        value=", ".join(missing) if missing else "all present",
        threshold=", ".join(str(path) for path in required_paths),
        message="API contract files required for service readiness.",
    )


def build_monitoring_snapshot(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    batch_score_dir: Path = DEFAULT_BATCH_SCORE_DIR,
    generated_at: datetime | None = None,
) -> MonitoringSnapshot:
    effective_generated_at = generated_at or datetime.now(UTC)
    checks: list[MonitoringCheck] = []
    if not db_path.exists():
        checks.append(
            MonitoringCheck(
                name="duckdb_database",
                status="fail",
                value=str(db_path),
                threshold="database file exists",
                message="DuckDB metrics layer is missing.",
            )
        )
    else:
        with duckdb.connect(str(db_path), read_only=True) as con:
            checks.extend(_availability_checks(con, db_path=db_path))
            checks.extend(_activation_checks(con))
            checks.extend(_experiment_guardrail_checks(con))
            checks.extend(_pricing_checks(con))
            checks.extend(_pricing_recommendation_checks(con))
    checks.append(_batch_scoring_check(batch_score_dir))
    checks.append(_api_contract_check())
    return MonitoringSnapshot(
        generated_at=effective_generated_at.isoformat(),
        db_path=str(db_path),
        overall_status=_status(checks),
        checks=checks,
    )


def render_markdown(snapshot: MonitoringSnapshot) -> str:
    lines = [
        "# Monitoring Snapshot",
        "",
        f"- Generated at: `{snapshot.generated_at}`",
        f"- DuckDB path: `{snapshot.db_path}`",
        f"- Overall status: `{snapshot.overall_status}`",
        "",
        "| Check | Status | Value | Threshold |",
        "| --- | --- | --- | --- |",
    ]
    for check in snapshot.checks:
        lines.append(
            f"| {check.name} | {check.status} | {check.value} | {check.threshold} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            *[f"- {check.name}: {check.message}" for check in snapshot.checks],
            "",
        ]
    )
    return "\n".join(lines)


def write_monitoring_snapshot(
    *,
    snapshot: MonitoringSnapshot,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    snapshot_date: date | None = None,
) -> SnapshotWriteResult:
    effective_date = snapshot_date or datetime.fromisoformat(snapshot.generated_at).date()
    partition_dir = output_dir / f"snapshot_date={effective_date.isoformat()}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    json_path = partition_dir / "monitoring_snapshot.json"
    markdown_path = partition_dir / "monitoring_snapshot.md"
    json_path.write_text(
        json.dumps(asdict(snapshot), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(snapshot), encoding="utf-8")
    return SnapshotWriteResult(
        json_path=json_path,
        markdown_path=markdown_path,
        snapshot=snapshot,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a monitoring snapshot.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--batch-score-dir", type=Path, default=DEFAULT_BATCH_SCORE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--snapshot-date", type=date.fromisoformat, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = build_monitoring_snapshot(
        db_path=args.db,
        batch_score_dir=args.batch_score_dir,
    )
    result = write_monitoring_snapshot(
        snapshot=snapshot,
        output_dir=args.output_dir,
        snapshot_date=args.snapshot_date,
    )
    print(
        f"Wrote monitoring snapshot to {result.json_path} and {result.markdown_path}; "
        f"overall status={snapshot.overall_status}."
    )


if __name__ == "__main__":
    main()
