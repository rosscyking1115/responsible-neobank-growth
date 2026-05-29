"""Persist pricing scenario and sensitivity analysis artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import duckdb
import pandas as pd

from api.schemas import PricingScenarioRequest, PricingScenarioResponse
from api.scoring import simulate_pricing_scenario

DEFAULT_OUTPUT_DIR = Path("artifacts/pricing/scenario_runs")
DEFAULT_SEGMENTS = ["student", "low", "middle", "high", "affluent"]
DEFAULT_INCENTIVES = [0.0, 2.0, 4.0, 6.0, 8.0]


@dataclass(frozen=True)
class SegmentPrior:
    segment: str
    eligible_customers: int
    baseline_activation_rate: float
    expected_monthly_margin_per_activated_customer_gbp: float
    vulnerable_customer_share: float
    source: str


@dataclass(frozen=True)
class ScenarioRunRow:
    scenario_id: str
    run_date: str
    segment: str
    current_incentive_gbp: float
    proposed_incentive_gbp: float
    eligible_customers: int
    baseline_activation_rate: float
    vulnerable_customer_share: float
    projected_activation_rate: float
    projected_lift_pp: float
    incremental_activated_customers: int
    incremental_incentive_cost_gbp: float
    expected_monthly_margin_gbp: float
    recommendation: Literal["ship", "iterate", "hold"]
    reason_codes: list[str]
    failed_guardrails: list[str]


@dataclass(frozen=True)
class SensitivityRunRow:
    scenario_id: str
    run_date: str
    segment: str
    proposed_incentive_gbp: float
    sensitivity_case: str
    margin_multiplier: float
    vulnerable_share_delta: float
    expected_monthly_margin_gbp: float
    projected_lift_pp: float
    recommendation: Literal["ship", "iterate", "hold"]


@dataclass(frozen=True)
class PricingScenarioRun:
    generated_at: str
    run_date: str
    db_path: str | None
    scenarios: list[ScenarioRunRow]
    sensitivity_rows: list[SensitivityRunRow]
    executive_summary: dict[str, int | float | str]


@dataclass(frozen=True)
class PricingScenarioWriteResult:
    json_path: Path
    markdown_path: Path
    scenario_csv_path: Path
    sensitivity_csv_path: Path
    run: PricingScenarioRun


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


def _fallback_priors() -> list[SegmentPrior]:
    defaults = {
        "student": (2500, 0.40, 3.2, 0.08),
        "low": (2200, 0.42, 3.6, 0.12),
        "middle": (3200, 0.47, 4.4, 0.06),
        "high": (1800, 0.51, 5.6, 0.03),
        "affluent": (1200, 0.54, 6.5, 0.02),
    }
    return [
        SegmentPrior(
            segment=segment,
            eligible_customers=eligible,
            baseline_activation_rate=activation,
            expected_monthly_margin_per_activated_customer_gbp=margin,
            vulnerable_customer_share=vulnerable_share,
            source="fallback",
        )
        for segment, (eligible, activation, margin, vulnerable_share) in defaults.items()
    ]


def load_segment_priors(db_path: Path | None) -> list[SegmentPrior]:
    if db_path is None or not db_path.exists():
        return _fallback_priors()

    query = """
        select
            activation.income_segment as segment,
            count(*) as eligible_customers,
            avg(case when activation.activated_d7 then 1.0 else 0.0 end)
                as baseline_activation_rate,
            avg(coalesce(clv.clv_proxy_12m_gbp, 0.0)) / 12.0
                as expected_monthly_margin_per_activated_customer_gbp,
            avg(case when activation.vulnerable_customer_flag then 1.0 else 0.0 end)
                as vulnerable_customer_share
        from main_marts.fct_activation as activation
        left join main_marts.fct_user_clv_proxy as clv
            on activation.user_id = clv.user_id
        group by 1
    """
    with duckdb.connect(str(db_path), read_only=True) as con:
        if not _table_exists(con, "fct_activation"):
            return _fallback_priors()
        rows = con.execute(query).fetchall()

    priors = [
        SegmentPrior(
            segment=str(row[0]),
            eligible_customers=int(row[1]),
            baseline_activation_rate=float(row[2] or 0.0),
            expected_monthly_margin_per_activated_customer_gbp=max(float(row[3] or 0.0), 0.5),
            vulnerable_customer_share=float(row[4] or 0.0),
            source="duckdb_mart",
        )
        for row in rows
    ]
    return priors or _fallback_priors()


def _request_from_prior(
    prior: SegmentPrior,
    *,
    proposed_incentive_gbp: float,
    current_incentive_gbp: float,
    margin_multiplier: float = 1.0,
    vulnerable_share_delta: float = 0.0,
) -> PricingScenarioRequest:
    return PricingScenarioRequest(
        segment=prior.segment,
        eligible_customers=prior.eligible_customers,
        baseline_activation_rate=prior.baseline_activation_rate,
        current_incentive_gbp=current_incentive_gbp,
        proposed_incentive_gbp=proposed_incentive_gbp,
        expected_monthly_margin_per_activated_customer_gbp=(
            prior.expected_monthly_margin_per_activated_customer_gbp * margin_multiplier
        ),
        vulnerable_customer_share=min(
            max(prior.vulnerable_customer_share + vulnerable_share_delta, 0.0),
            1.0,
        ),
    )


def _failed_guardrails(response: PricingScenarioResponse) -> list[str]:
    return [flag.name for flag in response.guardrails if not flag.passed]


def _scenario_id(segment: str, incentive: float) -> str:
    return f"{segment}-incentive-{incentive:.2f}".replace(".", "_")


def _scenario_row(
    *,
    run_date: date,
    request: PricingScenarioRequest,
    response: PricingScenarioResponse,
) -> ScenarioRunRow:
    return ScenarioRunRow(
        scenario_id=_scenario_id(request.segment, request.proposed_incentive_gbp),
        run_date=run_date.isoformat(),
        segment=request.segment,
        current_incentive_gbp=request.current_incentive_gbp,
        proposed_incentive_gbp=request.proposed_incentive_gbp,
        eligible_customers=request.eligible_customers,
        baseline_activation_rate=request.baseline_activation_rate,
        vulnerable_customer_share=request.vulnerable_customer_share,
        projected_activation_rate=response.projected_activation_rate,
        projected_lift_pp=response.projected_lift_pp,
        incremental_activated_customers=response.incremental_activated_customers,
        incremental_incentive_cost_gbp=response.incremental_incentive_cost_gbp,
        expected_monthly_margin_gbp=response.expected_monthly_margin_gbp,
        recommendation=response.recommendation,
        reason_codes=response.reason_codes,
        failed_guardrails=_failed_guardrails(response),
    )


def _sensitivity_rows(
    *,
    run_date: date,
    prior: SegmentPrior,
    scenario: ScenarioRunRow,
    current_incentive_gbp: float,
) -> list[SensitivityRunRow]:
    cases = [
        ("base", 1.0, 0.0),
        ("margin_downside", 0.75, 0.0),
        ("margin_upside", 1.25, 0.0),
        ("vulnerable_share_stress", 1.0, 0.05),
    ]
    rows = []
    for case_name, margin_multiplier, vulnerable_delta in cases:
        request = _request_from_prior(
            prior,
            proposed_incentive_gbp=scenario.proposed_incentive_gbp,
            current_incentive_gbp=current_incentive_gbp,
            margin_multiplier=margin_multiplier,
            vulnerable_share_delta=vulnerable_delta,
        )
        response = simulate_pricing_scenario(request)
        rows.append(
            SensitivityRunRow(
                scenario_id=scenario.scenario_id,
                run_date=run_date.isoformat(),
                segment=prior.segment,
                proposed_incentive_gbp=scenario.proposed_incentive_gbp,
                sensitivity_case=case_name,
                margin_multiplier=margin_multiplier,
                vulnerable_share_delta=vulnerable_delta,
                expected_monthly_margin_gbp=response.expected_monthly_margin_gbp,
                projected_lift_pp=response.projected_lift_pp,
                recommendation=response.recommendation,
            )
        )
    return rows


def _executive_summary(scenarios: list[ScenarioRunRow]) -> dict[str, int | float | str]:
    viable = [
        row
        for row in scenarios
        if row.recommendation in {"ship", "iterate"} and not row.failed_guardrails
    ]
    best = max(
        viable or scenarios,
        key=lambda row: (row.expected_monthly_margin_gbp, row.incremental_activated_customers),
    )
    return {
        "scenario_count": len(scenarios),
        "ship_count": sum(row.recommendation == "ship" for row in scenarios),
        "iterate_count": sum(row.recommendation == "iterate" for row in scenarios),
        "hold_count": sum(row.recommendation == "hold" for row in scenarios),
        "best_scenario_id": best.scenario_id,
        "best_segment": best.segment,
        "best_incentive_gbp": best.proposed_incentive_gbp,
        "best_expected_margin_gbp": best.expected_monthly_margin_gbp,
        "best_incremental_activated_customers": best.incremental_activated_customers,
    }


def build_pricing_scenario_run(
    *,
    db_path: Path | None = Path("neobank.duckdb"),
    incentives: list[float] | None = None,
    current_incentive_gbp: float = 0.0,
    run_date: date | None = None,
    generated_at: datetime | None = None,
) -> PricingScenarioRun:
    run_date = run_date or datetime.now(UTC).date()
    generated_at = generated_at or datetime.now(UTC)
    incentive_values = incentives or DEFAULT_INCENTIVES
    priors = load_segment_priors(db_path)
    scenario_rows: list[ScenarioRunRow] = []
    sensitivity_rows: list[SensitivityRunRow] = []

    for prior in priors:
        for incentive in incentive_values:
            request = _request_from_prior(
                prior,
                proposed_incentive_gbp=incentive,
                current_incentive_gbp=current_incentive_gbp,
            )
            response = simulate_pricing_scenario(request)
            scenario = _scenario_row(run_date=run_date, request=request, response=response)
            scenario_rows.append(scenario)
            sensitivity_rows.extend(
                _sensitivity_rows(
                    run_date=run_date,
                    prior=prior,
                    scenario=scenario,
                    current_incentive_gbp=current_incentive_gbp,
                )
            )

    return PricingScenarioRun(
        generated_at=generated_at.isoformat(),
        run_date=run_date.isoformat(),
        db_path=str(db_path) if db_path else None,
        scenarios=scenario_rows,
        sensitivity_rows=sensitivity_rows,
        executive_summary=_executive_summary(scenario_rows),
    )


def _rows_to_frame(rows: list[ScenarioRunRow] | list[SensitivityRunRow]) -> pd.DataFrame:
    return pd.DataFrame([asdict(row) for row in rows])


def render_markdown(run: PricingScenarioRun) -> str:
    summary = run.executive_summary
    top = sorted(
        run.scenarios,
        key=lambda row: row.expected_monthly_margin_gbp,
        reverse=True,
    )[:8]
    top_rows = "\n".join(
        "| "
        f"{row.scenario_id} | {row.segment} | {row.proposed_incentive_gbp:.2f} | "
        f"{row.projected_lift_pp:.2f} | {row.incremental_activated_customers} | "
        f"{row.expected_monthly_margin_gbp:.2f} | {row.recommendation} | "
        f"{', '.join(row.failed_guardrails) or 'none'} |"
        for row in top
    )
    recommendations = (
        f"`{summary['ship_count']}` ship, `{summary['iterate_count']}` iterate, "
        f"`{summary['hold_count']}` hold"
    )
    best = (
        f"`{summary['best_scenario_id']}` with expected margin GBP "
        f"`{summary['best_expected_margin_gbp']}`"
    )
    table_header = (
        "| Scenario | Segment | Incentive GBP | Lift pp | Incremental activations | "
        "Expected margin GBP | Recommendation | Failed guardrails |"
    )
    return f"""# Pricing Scenario Run

- Generated at: `{run.generated_at}`
- Run date: `{run.run_date}`
- DuckDB path: `{run.db_path or 'not used'}`
- Scenario count: `{summary['scenario_count']}`
- Recommendations: {recommendations}
- Best scenario: {best}

## Top Scenarios By Expected Margin

{table_header}
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
{top_rows}

## Operating Note

Treat `ship` as a candidate for controlled rollout, `iterate` as a candidate for
smaller experiment design, and `hold` as a stop state until unit economics or
customer guardrails improve. The sensitivity CSV should be reviewed before
selecting any scenario for a public narrative or production rollout.
"""


def write_pricing_scenario_run(
    *,
    run: PricingScenarioRun,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> PricingScenarioWriteResult:
    partition_dir = output_dir / f"run_date={run.run_date}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    json_path = partition_dir / "pricing_scenario_run.json"
    markdown_path = partition_dir / "pricing_scenario_run.md"
    scenario_csv_path = partition_dir / "pricing_scenarios.csv"
    sensitivity_csv_path = partition_dir / "pricing_sensitivity.csv"

    json_path.write_text(json.dumps(asdict(run), indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(run), encoding="utf-8")
    _rows_to_frame(run.scenarios).to_csv(scenario_csv_path, index=False)
    _rows_to_frame(run.sensitivity_rows).to_csv(sensitivity_csv_path, index=False)
    return PricingScenarioWriteResult(
        json_path=json_path,
        markdown_path=markdown_path,
        scenario_csv_path=scenario_csv_path,
        sensitivity_csv_path=sensitivity_csv_path,
        run=run,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Persist pricing scenario runs.")
    parser.add_argument("--db", type=Path, default=Path("neobank.duckdb"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-date", type=date.fromisoformat, default=None)
    parser.add_argument(
        "--incentives",
        type=float,
        nargs="+",
        default=None,
        help="Proposed incentive values in GBP.",
    )
    parser.add_argument("--current-incentive-gbp", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run = build_pricing_scenario_run(
        db_path=args.db,
        incentives=args.incentives,
        current_incentive_gbp=args.current_incentive_gbp,
        run_date=args.run_date,
    )
    result = write_pricing_scenario_run(run=run, output_dir=args.output_dir)
    print(
        f"Wrote {len(run.scenarios):,} pricing scenarios to {result.scenario_csv_path} "
        f"and sensitivity rows to {result.sensitivity_csv_path}."
    )


if __name__ == "__main__":
    main()
