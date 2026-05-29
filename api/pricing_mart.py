"""Read pricing scenario priors from the DuckDB mart when available."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import duckdb

from api.schemas import PricingScenarioRequest

PRICING_DUCKDB_ENV = "NEOBANK_DUCKDB_PATH"
DEFAULT_DUCKDB_PATH = Path("neobank.duckdb")


@dataclass(frozen=True)
class PricingMartSummary:
    source: str
    price_variant: str
    exposures: int
    acceptance_rate: float
    avg_net_margin_30d_gbp: float
    complaint_rate_14d: float
    human_review_rate: float
    recommended_action: str
    recommendation_reason_code: str


def configured_pricing_db_path() -> Path | None:
    configured = os.getenv(PRICING_DUCKDB_ENV)
    db_path = Path(configured) if configured else DEFAULT_DUCKDB_PATH
    return db_path if db_path.exists() else None


def scenario_price_variant(request: PricingScenarioRequest) -> str:
    if request.proposed_incentive_gbp <= 0:
        return "holdout"
    if request.proposed_incentive_gbp > request.current_incentive_gbp * 1.5:
        return "incentive"
    return "standard"


def _table_exists(con: duckdb.DuckDBPyConnection) -> bool:
    row = con.execute(
        """
        select count(*) > 0
        from information_schema.tables
        where table_schema = 'main_marts'
          and table_name = 'mart_pricing_recommendations'
        """
    ).fetchone()
    return bool(row[0]) if row else False


def _fetch_rows(
    con: duckdb.DuckDBPyConnection,
    *,
    segment: str | None,
    price_variant: str | None,
) -> list[dict[str, object]]:
    filters = []
    params: list[str] = []
    if segment is not None:
        filters.append("income_segment = ?")
        params.append(segment)
    if price_variant is not None:
        filters.append("price_variant = ?")
        params.append(price_variant)
    where_clause = f"where {' and '.join(filters)}" if filters else ""
    query = f"""
        select
            price_variant,
            exposures,
            acceptance_rate,
            avg_net_margin_30d_gbp,
            complaint_rate_14d,
            human_review_rate,
            recommended_action,
            recommendation_reason_code
        from main_marts.mart_pricing_recommendations
        {where_clause}
    """
    cursor = con.execute(query, params)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def load_pricing_mart_summary(request: PricingScenarioRequest) -> PricingMartSummary | None:
    db_path = configured_pricing_db_path()
    if db_path is None:
        return None

    price_variant = scenario_price_variant(request)
    with duckdb.connect(str(db_path), read_only=True) as con:
        if not _table_exists(con):
            return None
        rows = _fetch_rows(con, segment=request.segment, price_variant=price_variant)
        source = "segment_variant"
        if not rows:
            rows = _fetch_rows(con, segment=request.segment, price_variant=None)
            source = "segment"
        if not rows:
            rows = _fetch_rows(con, segment=None, price_variant=price_variant)
            source = "variant"
        if not rows:
            rows = _fetch_rows(con, segment=None, price_variant=None)
            source = "global"
    if not rows:
        return None

    exposures = sum(int(row["exposures"]) for row in rows)
    if exposures <= 0:
        return None

    def weighted_average(column: str) -> float:
        return float(
            sum(float(row[column]) * int(row["exposures"]) for row in rows) / exposures
        )

    top_row = max(rows, key=lambda row: int(row["exposures"]))
    return PricingMartSummary(
        source=source,
        price_variant=price_variant,
        exposures=exposures,
        acceptance_rate=weighted_average("acceptance_rate"),
        avg_net_margin_30d_gbp=weighted_average("avg_net_margin_30d_gbp"),
        complaint_rate_14d=weighted_average("complaint_rate_14d"),
        human_review_rate=weighted_average("human_review_rate"),
        recommended_action=str(top_row["recommended_action"]),
        recommendation_reason_code=str(top_row["recommendation_reason_code"]),
    )
