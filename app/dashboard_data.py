"""Data access and summary helpers for the Streamlit dashboard."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = Path("neobank.duckdb")
DEFAULT_DEMO_RAW_PATH = Path("raw/streamlit_demo")
PARTIAL_WEEK_DROP_RATIO = 0.70
DEMO_USERS = 5_000
DEMO_MONTHS = 6

ONBOARDING_EXPERIMENT = "personalised_onboarding_pot_prompt"
CUSTOMER_OUTCOME_SEGMENTS = [
    "digital_confidence_band",
    "income_band",
    "vulnerable_customer_proxy",
]
CUSTOMER_OUTCOME_FIELDS = ["activated_d7", "has_support_contact", "has_complaint"]
OUTCOME_LABELS = {
    "activated_d7": "D7 activation",
    "has_support_contact": "Support contact",
    "has_complaint": "Complaint",
}


@dataclass(frozen=True)
class DashboardData:
    overview: pd.Series
    weekly_engagement: pd.DataFrame
    activation_by_region: pd.DataFrame
    retention_curve: pd.DataFrame
    feature_adoption: pd.DataFrame
    clv_by_segment: pd.DataFrame
    pricing_outcomes: pd.DataFrame
    pricing_recommendations: pd.DataFrame
    experiment_variants: pd.DataFrame
    referral_daily: pd.DataFrame
    customer_outcomes: pd.DataFrame


def _fetch_frame(con: duckdb.DuckDBPyConnection, query: str) -> pd.DataFrame:
    return con.execute(query).fetchdf()


def _table_exists(con: duckdb.DuckDBPyConnection, schema_name: str, table_name: str) -> bool:
    result = con.execute(
        """
        select count(*) > 0
        from information_schema.tables
        where table_schema = ?
          and table_name = ?
        """,
        [schema_name, table_name],
    ).fetchone()
    return bool(result[0]) if result else False


def _empty_pricing_outcomes() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "offer_id",
            "exposure_date",
            "region",
            "price_variant",
            "exposures",
            "accepted_offers",
            "activated_offers",
            "acceptance_rate",
            "gross_margin_30d_gbp",
            "incentive_cost_gbp",
            "net_margin_30d_gbp",
            "support_contact_rate_14d",
            "complaint_rate_14d",
            "human_review_required_exposures",
        ]
    )


def _empty_pricing_recommendations() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "offer_id",
            "product_area",
            "offer_type",
            "income_segment",
            "price_variant",
            "exposures",
            "acceptance_rate",
            "avg_net_margin_30d_gbp",
            "total_net_margin_30d_gbp",
            "support_contact_rate_14d",
            "complaint_rate_14d",
            "human_review_rate",
            "recommended_action",
            "recommendation_reason_code",
        ]
    )


def _empty_customer_outcomes() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "user_id",
            "region",
            "income_segment",
            "income_band",
            "digital_confidence_band",
            "vulnerable_customer_proxy",
            "accessibility_need_proxy",
            "new_to_uk_proxy",
            "student_proxy",
            "activated_d7",
            "support_contact_count",
            "has_support_contact",
            "has_complaint",
        ]
    )


def resolve_project_path(path: Path) -> Path:
    """Resolve relative app paths from the repository root."""
    return path if path.is_absolute() else PROJECT_ROOT / path


def _run_bootstrap_command(command: list[str], *, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        output = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
        raise RuntimeError(f"Demo database bootstrap failed while running {command!r}:\n{output}")


def ensure_demo_database(
    db_path: Path = DEFAULT_DB_PATH,
    *,
    raw_path: Path = DEFAULT_DEMO_RAW_PATH,
    users: int = DEMO_USERS,
    months: int = DEMO_MONTHS,
) -> Path:
    """Create a small synthetic DuckDB database when the dashboard runs in a fresh cloud app."""
    resolved_db_path = resolve_project_path(db_path)
    if resolved_db_path.exists():
        return resolved_db_path

    resolved_raw_path = resolve_project_path(raw_path)
    resolved_raw_path.parent.mkdir(parents=True, exist_ok=True)

    _run_bootstrap_command(
        [
            sys.executable,
            "-m",
            "data_generator.generate",
            "--users",
            str(users),
            "--months",
            str(months),
            "--output-dir",
            str(resolved_raw_path),
        ]
    )
    env = os.environ.copy()
    env["NEOBANK_DUCKDB_PATH"] = str(resolved_db_path)
    _run_bootstrap_command(
        [
            sys.executable,
            "-m",
            "dbt.cli.main",
            "build",
            "--project-dir",
            "dbt_neobank",
            "--profiles-dir",
            "dbt_neobank",
            "--vars",
            f"{{raw_path: '{resolved_raw_path.as_posix()}'}}",
        ],
        env=env,
    )
    return resolved_db_path


def trim_partial_week(weekly_engagement: pd.DataFrame) -> pd.DataFrame:
    """Drop a final partial week when it is visibly incomplete versus the prior week."""
    if len(weekly_engagement) < 3:
        return weekly_engagement.copy()
    ordered = weekly_engagement.copy()
    ordered["activity_week"] = pd.to_datetime(ordered["activity_week"])
    ordered = ordered.sort_values("activity_week").reset_index(drop=True)
    last_wau = float(ordered.loc[len(ordered) - 1, "weekly_active_users"])
    prior_wau = float(ordered.loc[len(ordered) - 2, "weekly_active_users"])
    if prior_wau > 0 and last_wau < prior_wau * PARTIAL_WEEK_DROP_RATIO:
        return ordered.iloc[:-1].copy()
    return ordered


def load_dashboard_data(db_path: Path = DEFAULT_DB_PATH) -> DashboardData:
    """Load dashboard-ready frames from the dbt mart schemas."""
    resolved_db_path = resolve_project_path(db_path)
    if not resolved_db_path.exists():
        raise FileNotFoundError(
            f"{resolved_db_path} was not found. "
            "Build the dbt project before launching the dashboard."
        )

    with duckdb.connect(str(resolved_db_path), read_only=True) as con:
        overview = _fetch_frame(
            con,
            """
            select
                count(*) as users,
                avg(case when activation.activated_d7 then 1 else 0 end)
                    as d7_activation_rate,
                avg(case when activation.activated_ever then 1 else 0 end)
                    as activated_ever_rate,
                avg(activation.lifetime_transaction_count) as avg_lifetime_transactions,
                sum(activation.lifetime_card_spend_gbp) as total_card_spend_gbp,
                avg(clv.clv_proxy_12m_gbp) as avg_clv_proxy_12m_gbp
            from main_marts.fct_activation as activation
            inner join main_marts.fct_user_clv_proxy as clv
                on activation.user_id = clv.user_id
            """,
        ).iloc[0]
        weekly_engagement = _fetch_frame(
            con,
            """
            select
                activity_week,
                weekly_active_users,
                transactions,
                card_spend_gbp,
                transactions_per_active_user
            from main_marts.fct_weekly_engagement
            order by activity_week
            """,
        )
        activation_by_region = _fetch_frame(
            con,
            """
            select
                region,
                count(*) as users,
                avg(case when activated_d7 then 1 else 0 end) as d7_activation_rate,
                avg(lifetime_transaction_count) as avg_lifetime_transactions
            from main_marts.fct_activation
            group by 1
            order by users desc
            """,
        )
        retention_curve = _fetch_frame(
            con,
            """
            select
                weeks_since_signup,
                sum(retained_users)::double / nullif(sum(activated_users), 0) as retention_rate,
                sum(activated_users) as activated_users,
                sum(retained_users) as retained_users
            from main_marts.fct_retention_cohorts
            where weeks_since_signup between 1 and 12
            group by 1
            order by 1
            """,
        )
        feature_adoption = _fetch_frame(
            con,
            """
            select
                feature_name,
                adoption_month,
                adopting_users,
                adoption_events
            from main_marts.fct_feature_adoption
            order by adoption_month, feature_name
            """,
        )
        clv_by_segment = _fetch_frame(
            con,
            """
            select
                income_segment,
                count(*) as users,
                avg(clv_proxy_12m_gbp) as avg_clv_proxy_12m_gbp,
                avg(case when activated_d7 then 1 else 0 end) as d7_activation_rate
            from main_marts.fct_user_clv_proxy
            group by 1
            order by avg_clv_proxy_12m_gbp desc
            """,
        )
        if _table_exists(con, "main_marts", "fct_pricing_outcomes"):
            pricing_outcomes = _fetch_frame(
                con,
                """
                select
                    offer_id,
                    exposure_date,
                    region,
                    price_variant,
                    exposures,
                    accepted_offers,
                    activated_offers,
                    acceptance_rate,
                    gross_margin_30d_gbp,
                    incentive_cost_gbp,
                    net_margin_30d_gbp,
                    support_contact_rate_14d,
                    complaint_rate_14d,
                    human_review_required_exposures
                from main_marts.fct_pricing_outcomes
                order by exposure_date, offer_id, region, price_variant
                """,
            )
        else:
            pricing_outcomes = _empty_pricing_outcomes()
        if _table_exists(con, "main_marts", "mart_pricing_recommendations"):
            pricing_recommendations = _fetch_frame(
                con,
                """
                select
                    offer_id,
                    product_area,
                    offer_type,
                    income_segment,
                    price_variant,
                    exposures,
                    acceptance_rate,
                    avg_net_margin_30d_gbp,
                    total_net_margin_30d_gbp,
                    support_contact_rate_14d,
                    complaint_rate_14d,
                    human_review_rate,
                    recommended_action,
                    recommendation_reason_code
                from main_marts.mart_pricing_recommendations
                order by product_area, offer_id, income_segment, price_variant
                """,
            )
        else:
            pricing_recommendations = _empty_pricing_recommendations()
        experiment_variants = _fetch_frame(
            con,
            """
            select
                variant,
                count(*) as users,
                avg(case when activated_d7 then 1 else 0 end) as d7_activation_rate,
                avg(case when support_contacts > 0 then 1 else 0 end) as support_contact_rate,
                avg(case when complaints > 0 then 1 else 0 end) as complaint_rate,
                avg(case when app_crashes > 0 then 1 else 0 end) as app_crash_rate
            from main_marts.fct_experiment_user_metrics
            where experiment_name = 'personalised_onboarding_pot_prompt'
            group by 1
            order by 1
            """,
        )
        referral_daily = _fetch_frame(
            con,
            """
            select
                region,
                date_day,
                treated_region,
                post_period,
                incentive_active,
                signups,
                referral_signups,
                incremental_signups_ground_truth,
                reward_cost_gbp
            from main_marts.fct_region_daily_referrals
            order by date_day, region
            """,
        )
        if _table_exists(con, "main_marts", "fct_customer_outcomes"):
            customer_outcomes = _fetch_frame(
                con,
                """
                select
                    user_id,
                    region,
                    income_segment,
                    income_band,
                    digital_confidence_band,
                    vulnerable_customer_proxy,
                    accessibility_need_proxy,
                    new_to_uk_proxy,
                    student_proxy,
                    activated_d7,
                    support_contact_count,
                    has_support_contact,
                    has_complaint
                from main_marts.fct_customer_outcomes
                """,
            )
        else:
            customer_outcomes = _empty_customer_outcomes()

    return DashboardData(
        overview=overview,
        weekly_engagement=trim_partial_week(weekly_engagement),
        activation_by_region=activation_by_region,
        retention_curve=retention_curve,
        feature_adoption=feature_adoption,
        clv_by_segment=clv_by_segment,
        pricing_outcomes=pricing_outcomes,
        pricing_recommendations=pricing_recommendations,
        experiment_variants=experiment_variants,
        referral_daily=referral_daily,
        customer_outcomes=customer_outcomes,
    )


def onboarding_lift_pp(experiment_variants: pd.DataFrame) -> float | None:
    """Return treatment-control D7 activation lift in percentage points."""
    if experiment_variants.empty:
        return None
    rates = experiment_variants.set_index("variant")["d7_activation_rate"]
    if "control" not in rates or "treatment" not in rates:
        return None
    return float((rates["treatment"] - rates["control"]) * 100)


def referral_economics(referral_daily: pd.DataFrame) -> dict[str, float]:
    """Summarise observed treated-post referral economics from the geo mart."""
    if referral_daily.empty:
        return {
            "treated_post_referral_signups": 0.0,
            "reward_cost_gbp": 0.0,
            "embedded_incremental_signups": 0.0,
            "cost_per_embedded_incremental_signup": 0.0,
        }
    treated_post = referral_daily[
        referral_daily["treated_region"].astype(bool) & referral_daily["post_period"].astype(bool)
    ]
    referral_signups = float(treated_post["referral_signups"].sum())
    reward_cost = float(treated_post["reward_cost_gbp"].sum())
    embedded_incremental = float(treated_post["incremental_signups_ground_truth"].sum())
    cost_per_incremental = reward_cost / embedded_incremental if embedded_incremental else 0.0
    return {
        "treated_post_referral_signups": referral_signups,
        "reward_cost_gbp": reward_cost,
        "embedded_incremental_signups": embedded_incremental,
        "cost_per_embedded_incremental_signup": cost_per_incremental,
    }


def referral_grouped_daily(referral_daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate referral signups into treated and control series for charting."""
    if referral_daily.empty:
        return referral_daily.copy()
    grouped = referral_daily.copy()
    grouped["geo_group"] = grouped["treated_region"].map(
        {True: "Treated regions", False: "Control regions"}
    )
    return (
        grouped.groupby(["date_day", "geo_group"], as_index=False)
        .agg(
            referral_signups=("referral_signups", "sum"),
            signups=("signups", "sum"),
            reward_cost_gbp=("reward_cost_gbp", "sum"),
        )
        .sort_values(["date_day", "geo_group"])
    )


def pricing_economics(pricing_outcomes: pd.DataFrame) -> dict[str, float]:
    """Summarise pricing exposure, conversion, margin, and guardrail load."""
    if pricing_outcomes.empty:
        return {
            "exposures": 0.0,
            "acceptance_rate": 0.0,
            "net_margin_30d_gbp": 0.0,
            "incentive_cost_gbp": 0.0,
            "human_review_rate": 0.0,
            "complaint_rate_14d": 0.0,
        }
    exposures = float(pricing_outcomes["exposures"].sum())
    accepted = float(pricing_outcomes["accepted_offers"].sum())
    human_review = float(pricing_outcomes["human_review_required_exposures"].sum())
    weighted_complaints = (
        pricing_outcomes["complaint_rate_14d"] * pricing_outcomes["exposures"]
    ).sum()
    return {
        "exposures": exposures,
        "acceptance_rate": accepted / exposures if exposures else 0.0,
        "net_margin_30d_gbp": float(pricing_outcomes["net_margin_30d_gbp"].sum()),
        "incentive_cost_gbp": float(pricing_outcomes["incentive_cost_gbp"].sum()),
        "human_review_rate": human_review / exposures if exposures else 0.0,
        "complaint_rate_14d": float(weighted_complaints / exposures) if exposures else 0.0,
    }


def customer_outcome_gaps(
    customer_outcomes: pd.DataFrame,
    *,
    segments: list[str] | None = None,
    outcomes: list[str] | None = None,
    min_segment_size: int = 30,
) -> pd.DataFrame:
    """Disparity (in percentage points) for each outcome across each segment.

    Reuses ``src.wellbeing.metrics.outcome_gap`` so the dashboard and the analysis
    library share one definition of a fairness gap.
    """
    from src.wellbeing.metrics import outcome_gap

    columns = [
        "segment",
        "outcome",
        "outcome_label",
        "higher_rate_level",
        "lower_rate_level",
        "higher_rate",
        "lower_rate",
        "gap_pp",
    ]
    segments = segments or CUSTOMER_OUTCOME_SEGMENTS
    outcomes = outcomes or CUSTOMER_OUTCOME_FIELDS
    if customer_outcomes.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    for segment in segments:
        if segment not in customer_outcomes.columns:
            continue
        for outcome in outcomes:
            if outcome not in customer_outcomes.columns:
                continue
            gap = outcome_gap(
                customer_outcomes, segment, outcome, min_segment_size=min_segment_size
            )
            if gap is None:
                continue
            rows.append(
                {
                    "segment": segment,
                    "outcome": outcome,
                    "outcome_label": OUTCOME_LABELS.get(outcome, outcome),
                    "higher_rate_level": gap.best_level,
                    "lower_rate_level": gap.worst_level,
                    "higher_rate": gap.best_rate,
                    "lower_rate": gap.worst_rate,
                    "gap_pp": gap.gap * 100,
                }
            )
    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values("gap_pp", ascending=False)
        .reset_index(drop=True)
    )


def _two_proportion_evidence_strength(rates: pd.DataFrame) -> float:
    """One-sided confidence that treatment activation exceeds control.

    Uses a numpy/stdlib two-proportion z-test (no scipy) so it runs inside the
    slim Streamlit Cloud dependency set. Returns 0..1 (``1 - one_sided_p_value``).
    """
    import math

    control = rates.loc["control"]
    treatment = rates.loc["treatment"]
    n_c = int(control["users"])
    n_t = int(treatment["users"])
    if n_c == 0 or n_t == 0:
        return 0.0
    p_c = float(control["d7_activation_rate"])
    p_t = float(treatment["d7_activation_rate"])
    p_pool = (p_c * n_c + p_t * n_t) / (n_c + n_t)
    se = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n_c + 1.0 / n_t))
    if se == 0:
        return 0.0
    z = (p_t - p_c) / se
    one_sided_p = 0.5 * math.erfc(z / math.sqrt(2))
    return max(0.0, min(1.0, 1.0 - one_sided_p))


def onboarding_release_decision(
    experiment_variants: pd.DataFrame,
    customer_outcomes: pd.DataFrame | None = None,
):
    """Combine the onboarding A/B readout and fairness gaps into a release decision.

    Returns a ``ReleaseDecision`` (or ``None`` if the experiment data is missing),
    wiring the release-gate engine to live dashboard signals.
    """
    from src.release_decisions import ReleaseSignals, decide

    if experiment_variants.empty:
        return None
    rates = experiment_variants.set_index("variant")
    if "control" not in rates.index or "treatment" not in rates.index:
        return None

    lift = onboarding_lift_pp(experiment_variants) or 0.0
    support_delta = float(
        rates.loc["treatment", "support_contact_rate"]
        - rates.loc["control", "support_contact_rate"]
    )
    complaint_delta = float(
        rates.loc["treatment", "complaint_rate"] - rates.loc["control", "complaint_rate"]
    )
    fairness_gap = 0.0
    if customer_outcomes is not None and not customer_outcomes.empty:
        activation_gaps = customer_outcome_gaps(customer_outcomes, outcomes=["activated_d7"])
        if not activation_gaps.empty:
            fairness_gap = float(activation_gaps["gap_pp"].max()) / 100.0

    signals = ReleaseSignals(
        feature_name=ONBOARDING_EXPERIMENT,
        business_uplift=lift / 100.0,
        evidence_strength=_two_proportion_evidence_strength(rates),
        complaint_rate_delta=complaint_delta,
        support_burden_delta=support_delta,
        fairness_gap=fairness_gap,
    )
    return decide(signals)


def pricing_margin_by_offer(pricing_recommendations: pd.DataFrame) -> pd.DataFrame:
    """Aggregate recommendation mart rows into offer-level margin and guardrail summaries."""
    if pricing_recommendations.empty:
        return pricing_recommendations.copy()
    return (
        pricing_recommendations.groupby(["offer_id", "product_area"], as_index=False)
        .agg(
            exposures=("exposures", "sum"),
            total_net_margin_30d_gbp=("total_net_margin_30d_gbp", "sum"),
            acceptance_rate=("acceptance_rate", "mean"),
            human_review_rate=("human_review_rate", "mean"),
        )
        .sort_values("total_net_margin_30d_gbp", ascending=False)
    )


def offer_fair_value(pricing_recommendations: pd.DataFrame) -> pd.DataFrame:
    """Offer-level fair-value score and fairness-aware governance action.

    Aggregates the recommendation mart to one exposure-weighted row per offer, then
    applies ``src.pricing_governance`` so commercially attractive but unfair offers
    are downgraded.
    """
    from src.pricing_governance import assess_offers

    if pricing_recommendations.empty:
        return assess_offers(pd.DataFrame())

    def _weighted(group: pd.DataFrame, column: str) -> float:
        weight = float(group["exposures"].sum())
        if weight == 0:
            return 0.0
        return float((group[column] * group["exposures"]).sum() / weight)

    offer_rows: list[dict[str, object]] = []
    for offer_id, group in pricing_recommendations.groupby("offer_id"):
        dominant = group.sort_values("exposures", ascending=False).iloc[0]["recommended_action"]
        offer_rows.append(
            {
                "offer_id": offer_id,
                "exposures": int(group["exposures"].sum()),
                "complaint_rate_14d": _weighted(group, "complaint_rate_14d"),
                "support_contact_rate_14d": _weighted(group, "support_contact_rate_14d"),
                "human_review_rate": _weighted(group, "human_review_rate"),
                "recommended_action": dominant,
            }
        )
    assessed = assess_offers(pd.DataFrame(offer_rows))
    exposures = pd.DataFrame(offer_rows)[["offer_id", "exposures"]]
    return assessed.merge(exposures, on="offer_id", how="left")
