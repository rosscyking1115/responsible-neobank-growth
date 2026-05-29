from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from src.monitoring.snapshot import MonitoringSnapshot, build_monitoring_snapshot
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.monitoring.snapshot import MonitoringSnapshot, build_monitoring_snapshot

try:
    from app.dashboard_data import (
        DEFAULT_DB_PATH,
        DashboardData,
        ensure_demo_database,
        load_dashboard_data,
        onboarding_lift_pp,
        pricing_economics,
        pricing_margin_by_offer,
        referral_economics,
        referral_grouped_daily,
    )
except ModuleNotFoundError:
    from dashboard_data import (  # type: ignore[no-redef]
        DEFAULT_DB_PATH,
        DashboardData,
        ensure_demo_database,
        load_dashboard_data,
        onboarding_lift_pp,
        pricing_economics,
        pricing_margin_by_offer,
        referral_economics,
        referral_grouped_daily,
    )

st.set_page_config(
    page_title="Neobank Product Analytics",
    layout="wide",
    initial_sidebar_state="collapsed",
)

FEATURE_COLORS = {
    "easy_access_savings": "#0B6B75",
    "referrals": "#00A88F",
    "salary_sorter": "#F2B544",
    "savings_pot": "#7C6FE8",
}
VARIANT_COLORS = {"control": "#6B7280", "treatment": "#00A88F"}
PRICING_ACTION_COLORS = {
    "scale": "#00A88F",
    "test": "#0B66C3",
    "hold_margin": "#F2B544",
    "hold_guardrail": "#EF4444",
    "human_review": "#7C6FE8",
}
PRIMARY_BLUE = "#0B66C3"
STATUS_COLORS = {"pass": "#00A88F", "warn": "#F2B544", "fail": "#EF4444"}


def _apply_app_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1180px;
            padding-top: 3rem;
            padding-bottom: 3rem;
        }
        a[href^="#"] {
            display: none;
        }
        div[data-testid="stMetric"] label {
            color: #111827;
            font-size: 0.95rem;
        }
        div[data-testid="stMetricValue"] {
            color: #202436;
            font-size: 2.35rem;
        }
        div[data-testid="stMarkdownContainer"] h3 {
            margin-top: 1.6rem;
            margin-bottom: 0.7rem;
        }
        div[data-testid="stMarkdownContainer"] li {
            margin-bottom: 0.35rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def cached_dashboard_data(db_path: str) -> DashboardData:
    prepared_db_path = ensure_demo_database(Path(db_path))
    return load_dashboard_data(prepared_db_path)


@st.cache_data(show_spinner=False)
def cached_monitoring_snapshot(db_path: str) -> MonitoringSnapshot:
    prepared_db_path = ensure_demo_database(Path(db_path))
    return build_monitoring_snapshot(db_path=prepared_db_path)


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _gbp(value: float) -> str:
    return f"GBP {value:,.0f}"


def _apply_chart_layout(fig, *, height: int) -> None:
    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        template="plotly_white",
        font={"family": "Inter, Segoe UI, sans-serif"},
        legend_title_text="",
    )


def _metric_grid(data: DashboardData) -> None:
    overview = data.overview
    lift = onboarding_lift_pp(data.experiment_variants)
    referral = referral_economics(data.referral_daily)
    cols = st.columns(5)
    cols[0].metric("Users", f"{int(overview['users']):,}")
    cols[1].metric("D7 activation", _pct(float(overview["d7_activation_rate"])))
    cols[2].metric("Avg CLV proxy", _gbp(float(overview["avg_clv_proxy_12m_gbp"])))
    cols[3].metric("Onboarding lift", f"{lift:.2f} pp" if lift is not None else "n/a")
    cols[4].metric(
        "Referral cost / embedded lift",
        _gbp(referral["cost_per_embedded_incremental_signup"]),
    )


def _render_product_health(data: DashboardData) -> None:
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Weekly Engagement")
        fig = px.line(
            data.weekly_engagement,
            x="activity_week",
            y="weekly_active_users",
            markers=True,
            labels={"activity_week": "Week", "weekly_active_users": "WAU"},
        )
        fig.update_traces(line_color=PRIMARY_BLUE, marker_color=PRIMARY_BLUE)
        _apply_chart_layout(fig, height=330)
        st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader("D7 Activation By Region")
        region_frame = data.activation_by_region.sort_values("d7_activation_rate")
        fig = px.bar(
            region_frame,
            x="d7_activation_rate",
            y="region",
            orientation="h",
            labels={"d7_activation_rate": "D7 activation", "region": "Region"},
            hover_data=["users", "avg_lifetime_transactions"],
        )
        fig.update_traces(marker_color=PRIMARY_BLUE)
        _apply_chart_layout(fig, height=330)
        fig.update_xaxes(tickformat=".0%")
        st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    with left:
        st.subheader("Post-Activation Retention")
        fig = px.line(
            data.retention_curve,
            x="weeks_since_signup",
            y="retention_rate",
            markers=True,
            labels={"weeks_since_signup": "Weeks since signup", "retention_rate": "Retention"},
        )
        fig.update_traces(line_color=PRIMARY_BLUE, marker_color=PRIMARY_BLUE)
        _apply_chart_layout(fig, height=320)
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader("Feature Adoption")
        fig = px.bar(
            data.feature_adoption,
            x="adoption_month",
            y="adopting_users",
            color="feature_name",
            color_discrete_map=FEATURE_COLORS,
            labels={
                "adoption_month": "Month",
                "adopting_users": "Adopting users",
                "feature_name": "Feature",
            },
        )
        _apply_chart_layout(fig, height=320)
        st.plotly_chart(fig, width="stretch")

    st.subheader("Value By Income Segment")
    fig = px.bar(
        data.clv_by_segment,
        x="income_segment",
        y="avg_clv_proxy_12m_gbp",
        color="d7_activation_rate",
        color_continuous_scale=["#DCEFF7", "#8DD7D0", "#006C67"],
        labels={
            "income_segment": "Income segment",
            "avg_clv_proxy_12m_gbp": "Avg CLV proxy",
            "d7_activation_rate": "D7 activation",
        },
        hover_data=["users"],
    )
    _apply_chart_layout(fig, height=330)
    st.plotly_chart(fig, width="stretch")


def _render_experiments(data: DashboardData) -> None:
    onboarding, referral = st.columns(2)
    with onboarding:
        st.subheader("Onboarding A/B")
        lift = onboarding_lift_pp(data.experiment_variants)
        st.metric("Treatment lift", f"{lift:.2f} pp" if lift is not None else "n/a")
        fig = px.bar(
            data.experiment_variants,
            x="variant",
            y="d7_activation_rate",
            color="variant",
            color_discrete_map=VARIANT_COLORS,
            labels={"variant": "Variant", "d7_activation_rate": "D7 activation"},
            hover_data=["users", "support_contact_rate", "complaint_rate", "app_crash_rate"],
        )
        _apply_chart_layout(fig, height=330)
        fig.update_layout(showlegend=False)
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, width="stretch")

    with referral:
        st.subheader("Referral Geo Incrementality")
        economics = referral_economics(data.referral_daily)
        st.metric("Observed reward cost", _gbp(economics["reward_cost_gbp"]))
        st.metric(
            "Embedded incremental signups",
            f"{economics['embedded_incremental_signups']:,.0f}",
        )
        grouped = referral_grouped_daily(data.referral_daily)
        fig = px.line(
            grouped,
            x="date_day",
            y="referral_signups",
            color="geo_group",
            color_discrete_map={"Control regions": "#6B7280", "Treated regions": "#00A88F"},
            labels={
                "date_day": "Date",
                "referral_signups": "Referral signups",
                "geo_group": "Geo group",
            },
        )
        _apply_chart_layout(fig, height=340)
        st.plotly_chart(fig, width="stretch")


def _render_pricing(data: DashboardData) -> None:
    economics = pricing_economics(data.pricing_outcomes)
    cols = st.columns(5)
    cols[0].metric("Offer exposures", f"{economics['exposures']:,.0f}")
    cols[1].metric("Acceptance rate", _pct(economics["acceptance_rate"]))
    cols[2].metric("Net margin 30d", _gbp(economics["net_margin_30d_gbp"]))
    cols[3].metric("Incentive cost", _gbp(economics["incentive_cost_gbp"]))
    cols[4].metric("Human review rate", _pct(economics["human_review_rate"]))

    if data.pricing_recommendations.empty:
        st.info("Pricing marts are not available in this DuckDB build.")
        return

    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Recommendation Actions")
        action_frame = (
            data.pricing_recommendations.groupby(
                ["recommended_action", "recommendation_reason_code"],
                as_index=False,
            )
            .agg(exposures=("exposures", "sum"))
            .sort_values("exposures", ascending=False)
        )
        fig = px.bar(
            action_frame,
            x="recommended_action",
            y="exposures",
            color="recommended_action",
            color_discrete_map=PRICING_ACTION_COLORS,
            labels={
                "recommended_action": "Action",
                "exposures": "Eligible exposures",
                "recommendation_reason_code": "Reason",
            },
            hover_data=["recommendation_reason_code"],
        )
        _apply_chart_layout(fig, height=320)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader("Margin By Offer")
        margin_frame = pricing_margin_by_offer(data.pricing_recommendations)
        fig = px.bar(
            margin_frame,
            x="total_net_margin_30d_gbp",
            y="offer_id",
            orientation="h",
            color="human_review_rate",
            color_continuous_scale=["#DCEFF7", "#8DD7D0", "#006C67"],
            labels={
                "total_net_margin_30d_gbp": "Net margin 30d",
                "offer_id": "Offer",
                "human_review_rate": "Human review",
            },
            hover_data=["product_area", "exposures", "acceptance_rate"],
        )
        _apply_chart_layout(fig, height=320)
        st.plotly_chart(fig, width="stretch")

    st.subheader("Pricing Guardrails By Variant")
    variant_frame = (
        data.pricing_recommendations.groupby(["price_variant"], as_index=False)
        .agg(
            exposures=("exposures", "sum"),
            acceptance_rate=("acceptance_rate", "mean"),
            avg_net_margin_30d_gbp=("avg_net_margin_30d_gbp", "mean"),
            complaint_rate_14d=("complaint_rate_14d", "mean"),
            human_review_rate=("human_review_rate", "mean"),
        )
        .sort_values("price_variant")
    )
    fig = px.scatter(
        variant_frame,
        x="acceptance_rate",
        y="avg_net_margin_30d_gbp",
        size="exposures",
        color="human_review_rate",
        color_continuous_scale=["#DCEFF7", "#8DD7D0", "#006C67"],
        labels={
            "acceptance_rate": "Acceptance rate",
            "avg_net_margin_30d_gbp": "Avg net margin 30d",
            "exposures": "Exposures",
            "human_review_rate": "Human review",
        },
        hover_name="price_variant",
        hover_data=["complaint_rate_14d"],
    )
    _apply_chart_layout(fig, height=330)
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")


def _render_monitoring(snapshot: MonitoringSnapshot) -> None:
    checks = pd.DataFrame(
        [
            {
                "check": check.name,
                "status": check.status,
                "value": check.value,
                "threshold": check.threshold,
                "message": check.message,
            }
            for check in snapshot.checks
        ]
    )
    status_counts = (
        checks["status"]
        .value_counts()
        .reindex(["fail", "warn", "pass"], fill_value=0)
        .rename_axis("status")
        .reset_index(name="checks")
    )

    cols = st.columns(4)
    cols[0].metric("Overall status", snapshot.overall_status.upper())
    cols[1].metric("Failing checks", int(status_counts.loc[0, "checks"]))
    cols[2].metric("Warnings", int(status_counts.loc[1, "checks"]))
    cols[3].metric("Passing checks", int(status_counts.loc[2, "checks"]))

    left, right = st.columns([0.8, 1.2])
    with left:
        st.subheader("Check Status")
        fig = px.bar(
            status_counts,
            x="status",
            y="checks",
            color="status",
            color_discrete_map=STATUS_COLORS,
            labels={"status": "Status", "checks": "Checks"},
        )
        _apply_chart_layout(fig, height=300)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader("Attention Required")
        attention = checks[checks["status"].isin(["fail", "warn"])].copy()
        if attention.empty:
            st.dataframe(
                checks[["check", "status", "value", "threshold"]],
                width="stretch",
                hide_index=True,
            )
        else:
            st.dataframe(
                attention[["check", "status", "value", "threshold", "message"]],
                width="stretch",
                hide_index=True,
            )

    st.subheader("All Checks")
    status_order = {"fail": 0, "warn": 1, "pass": 2}
    ordered = checks.assign(status_order=checks["status"].map(status_order)).sort_values(
        ["status_order", "check"]
    )
    st.dataframe(
        ordered[["check", "status", "value", "threshold"]],
        width="stretch",
        hide_index=True,
    )


def main() -> None:
    _apply_app_style()
    st.title("Neobank Product Analytics")

    db_path = str(DEFAULT_DB_PATH)

    try:
        data = cached_dashboard_data(db_path)
        monitoring_snapshot = cached_monitoring_snapshot(db_path)
    except Exception as exc:  # pragma: no cover - Streamlit-only failure path.
        st.error(str(exc))
        st.stop()

    _metric_grid(data)
    product_tab, pricing_tab, experiment_tab, monitoring_tab = st.tabs(
        ["Product health", "Pricing intelligence", "Experiments", "Monitoring"]
    )
    with product_tab:
        _render_product_health(data)
    with pricing_tab:
        _render_pricing(data)
    with experiment_tab:
        _render_experiments(data)
    with monitoring_tab:
        _render_monitoring(monitoring_snapshot)


if __name__ == "__main__":
    main()
