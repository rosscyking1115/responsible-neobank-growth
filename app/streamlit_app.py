from __future__ import annotations

from pathlib import Path

import plotly.express as px
import streamlit as st

try:
    from app.dashboard_data import (
        DEFAULT_DB_PATH,
        DashboardData,
        load_dashboard_data,
        onboarding_lift_pp,
        read_decision_memos,
        referral_economics,
        referral_grouped_daily,
    )
except ModuleNotFoundError:
    from dashboard_data import (  # type: ignore[no-redef]
        DEFAULT_DB_PATH,
        DashboardData,
        load_dashboard_data,
        onboarding_lift_pp,
        read_decision_memos,
        referral_economics,
        referral_grouped_daily,
    )

st.set_page_config(page_title="Neobank Product Analytics", layout="wide")


@st.cache_data(show_spinner=False)
def cached_dashboard_data(db_path: str) -> DashboardData:
    return load_dashboard_data(Path(db_path))


@st.cache_data(show_spinner=False)
def cached_memos(memo_dir: str) -> dict[str, str]:
    return read_decision_memos(Path(memo_dir))


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _gbp(value: float) -> str:
    return f"GBP {value:,.0f}"


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
        fig.update_layout(margin={"l": 10, "r": 10, "t": 10, "b": 10}, height=330)
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
        fig.update_layout(margin={"l": 10, "r": 10, "t": 10, "b": 10}, height=330)
        fig.update_xaxes(tickformat=".0%")
        st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    with left:
        st.subheader("Activated Cohort Retention")
        fig = px.line(
            data.retention_curve,
            x="weeks_since_signup",
            y="retention_rate",
            markers=True,
            labels={"weeks_since_signup": "Weeks since signup", "retention_rate": "Retention"},
        )
        fig.update_layout(margin={"l": 10, "r": 10, "t": 10, "b": 10}, height=320)
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader("Feature Adoption")
        fig = px.bar(
            data.feature_adoption,
            x="adoption_month",
            y="adopting_users",
            color="feature_name",
            labels={
                "adoption_month": "Month",
                "adopting_users": "Adopting users",
                "feature_name": "Feature",
            },
        )
        fig.update_layout(margin={"l": 10, "r": 10, "t": 10, "b": 10}, height=320)
        st.plotly_chart(fig, width="stretch")

    st.subheader("Value By Income Segment")
    fig = px.bar(
        data.clv_by_segment,
        x="income_segment",
        y="avg_clv_proxy_12m_gbp",
        color="d7_activation_rate",
        labels={
            "income_segment": "Income segment",
            "avg_clv_proxy_12m_gbp": "Avg CLV proxy",
            "d7_activation_rate": "D7 activation",
        },
        hover_data=["users"],
    )
    fig.update_layout(margin={"l": 10, "r": 10, "t": 10, "b": 10}, height=330)
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
            labels={"variant": "Variant", "d7_activation_rate": "D7 activation"},
            hover_data=["users", "support_contact_rate", "complaint_rate", "app_crash_rate"],
        )
        fig.update_layout(showlegend=False, margin={"l": 10, "r": 10, "t": 10, "b": 10})
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
            labels={
                "date_day": "Date",
                "referral_signups": "Referral signups",
                "geo_group": "Geo group",
            },
        )
        fig.update_layout(margin={"l": 10, "r": 10, "t": 10, "b": 10}, height=340)
        st.plotly_chart(fig, width="stretch")


def _render_memos(memo_dir: str) -> None:
    memos = cached_memos(memo_dir)
    left, right = st.columns(2)
    with left:
        st.subheader("Onboarding Decision")
        st.markdown(memos["Onboarding A/B"])
    with right:
        st.subheader("Referral Decision")
        st.markdown(memos["Referral Geo"])


def main() -> None:
    st.title("Neobank Product Analytics")

    with st.sidebar:
        db_path = st.text_input("DuckDB path", value=str(DEFAULT_DB_PATH))
        memo_dir = st.text_input("Memo directory", value="docs/memos")

    try:
        data = cached_dashboard_data(db_path)
    except Exception as exc:  # pragma: no cover - Streamlit-only failure path.
        st.error(str(exc))
        st.stop()

    _metric_grid(data)
    product_tab, experiment_tab, memo_tab = st.tabs(
        ["Product health", "Experiments", "Decision memos"]
    )
    with product_tab:
        _render_product_health(data)
    with experiment_tab:
        _render_experiments(data)
    with memo_tab:
        _render_memos(memo_dir)


if __name__ == "__main__":
    main()
