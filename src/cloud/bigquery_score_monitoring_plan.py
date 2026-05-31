"""Render BigQuery monitoring queries for activation score tables."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date

PROJECT_ENV_REF = "${GCP_PROJECT_ID}"
LOCATION_ENV_REF = "${NEOBANK_BQ_LOCATION}"
DATASET_ENV_REF = "${NEOBANK_BQ_ML_DATASET}"
TABLE_NAME = "customer_scores_daily"


@dataclass(frozen=True)
class ScoreMonitoringPlan:
    score_date: date
    project: str
    dataset: str
    location: str
    table: str
    min_rows: int
    max_vulnerable_review_rate: float

    @property
    def table_ref(self) -> str:
        return f"{self.project}.{self.dataset}.{self.table}"


def build_score_monitoring_plan(
    *,
    score_date: date,
    project: str = PROJECT_ENV_REF,
    dataset: str = DATASET_ENV_REF,
    location: str = LOCATION_ENV_REF,
    table: str = TABLE_NAME,
    min_rows: int = 100,
    max_vulnerable_review_rate: float = 0.10,
) -> ScoreMonitoringPlan:
    return ScoreMonitoringPlan(
        score_date=score_date,
        project=project,
        dataset=dataset,
        location=location,
        table=table,
        min_rows=min_rows,
        max_vulnerable_review_rate=max_vulnerable_review_rate,
    )


def render_score_monitoring_sql(plan: ScoreMonitoringPlan) -> str:
    score_date = plan.score_date.isoformat()
    return f"""
WITH score_slice AS (
  SELECT
    DATE(score_date) AS score_date,
    user_id,
    model_version,
    activation_probability,
    decision,
    vulnerable_customer_review
  FROM `{plan.table_ref}`
  WHERE DATE(score_date) = DATE '{score_date}'
),
summary AS (
  SELECT
    score_date,
    COUNT(*) AS scored_users,
    COUNT(DISTINCT user_id) AS unique_users,
    COUNT(DISTINCT model_version) AS model_versions,
    COUNTIF(decision = 'target') AS targeted_users,
    SAFE_DIVIDE(COUNTIF(decision = 'target'), COUNT(*)) AS targeting_rate,
    COUNTIF(vulnerable_customer_review) AS vulnerable_review_users,
    SAFE_DIVIDE(COUNTIF(vulnerable_customer_review), COUNT(*)) AS vulnerable_review_rate,
    MIN(activation_probability) AS min_activation_probability,
    AVG(activation_probability) AS avg_activation_probability,
    MAX(activation_probability) AS max_activation_probability,
    APPROX_QUANTILES(activation_probability, 100)[OFFSET(10)] AS p10_activation_probability,
    APPROX_QUANTILES(activation_probability, 100)[OFFSET(50)] AS p50_activation_probability,
    APPROX_QUANTILES(activation_probability, 100)[OFFSET(90)] AS p90_activation_probability
  FROM score_slice
  GROUP BY score_date
)
SELECT
  *,
  CASE
    WHEN scored_users < {plan.min_rows} THEN 'fail'
    WHEN unique_users != scored_users THEN 'fail'
    WHEN min_activation_probability < 0 OR max_activation_probability > 1 THEN 'fail'
    WHEN targeting_rate < 0.01 OR targeting_rate > 0.60 THEN 'warn'
    WHEN vulnerable_review_rate > {plan.max_vulnerable_review_rate:.6f} THEN 'warn'
    ELSE 'pass'
  END AS monitoring_status
FROM summary
ORDER BY score_date
""".strip()


def render_bq_query_command(plan: ScoreMonitoringPlan) -> str:
    powershell_sql = render_score_monitoring_sql(plan).replace("'", "''")
    return f"bq --location={plan.location} query --use_legacy_sql=false '{powershell_sql}'"


def render_score_monitoring_plan(plan: ScoreMonitoringPlan) -> str:
    return "\n".join(
        [
            "# BigQuery Activation Score Monitoring Plan",
            "",
            f"Score date: {plan.score_date.isoformat()}",
            f"BigQuery table: `{plan.table_ref}`",
            f"Minimum scored users: {plan.min_rows:,}",
            f"Maximum vulnerable-review rate: {plan.max_vulnerable_review_rate:.2%}",
            "",
            "```powershell",
            render_bq_query_command(plan),
            "```",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render BigQuery score monitoring query.")
    parser.add_argument("--score-date", type=date.fromisoformat, required=True)
    parser.add_argument("--project", default=PROJECT_ENV_REF)
    parser.add_argument("--dataset", default=DATASET_ENV_REF)
    parser.add_argument("--location", default=LOCATION_ENV_REF)
    parser.add_argument("--table", default=TABLE_NAME)
    parser.add_argument("--min-rows", type=int, default=100)
    parser.add_argument("--max-vulnerable-review-rate", type=float, default=0.10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = build_score_monitoring_plan(
        score_date=args.score_date,
        project=args.project,
        dataset=args.dataset,
        location=args.location,
        table=args.table,
        min_rows=args.min_rows,
        max_vulnerable_review_rate=args.max_vulnerable_review_rate,
    )
    print(render_score_monitoring_plan(plan))


if __name__ == "__main__":
    main()
