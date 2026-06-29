from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from src.monitoring.snapshot import MonitoringSnapshot, build_monitoring_snapshot
    from src.pricing.scenario_runs import PricingScenarioRun, build_pricing_scenario_run
    from src.reports import build_report, render_html, report_excel_bytes
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.monitoring.snapshot import MonitoringSnapshot, build_monitoring_snapshot
    from src.pricing.scenario_runs import PricingScenarioRun, build_pricing_scenario_run
    from src.reports import build_report, render_html, report_excel_bytes

try:
    from app.dashboard_data import (
        DEFAULT_DB_PATH,
        DashboardData,
        customer_outcome_gaps,
        ensure_demo_database,
        load_dashboard_data,
        offer_fair_value,
        onboarding_abandonment_by_segment,
        onboarding_funnel_steps,
        onboarding_lift_pp,
        onboarding_release_decision,
        pricing_economics,
        pricing_margin_by_offer,
        protection_intervention_summary,
        referral_economics,
        referral_grouped_daily,
    )
except ModuleNotFoundError:
    from dashboard_data import (  # type: ignore[no-redef]
        DEFAULT_DB_PATH,
        DashboardData,
        customer_outcome_gaps,
        ensure_demo_database,
        load_dashboard_data,
        offer_fair_value,
        onboarding_abandonment_by_segment,
        onboarding_funnel_steps,
        onboarding_lift_pp,
        onboarding_release_decision,
        pricing_economics,
        pricing_margin_by_offer,
        protection_intervention_summary,
        referral_economics,
        referral_grouped_daily,
    )

st.set_page_config(
    page_title="Responsible Neobank Growth Platform",
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
DECISION_COLORS = {
    "ship": "#00A88F",
    "limited_rollout": "#0B66C3",
    "experiment_only": "#F2B544",
    "needs_human_review": "#7C6FE8",
    "block": "#EF4444",
}
DECISION_LABELS = {
    "ship": "SHIP",
    "limited_rollout": "LIMITED ROLLOUT",
    "experiment_only": "EXPERIMENT ONLY",
    "needs_human_review": "NEEDS HUMAN REVIEW",
    "block": "BLOCK",
}
GOVERNANCE_COLORS = {
    "scale": "#00A88F",
    "monitor": "#0B66C3",
    "hold_fair_value": "#F2B544",
    "human_review": "#7C6FE8",
}
PROTECTION_COLORS = {
    "no_action": "#6B7280",
    "education_prompt": "#0B66C3",
    "soft_friction": "#F2B544",
    "cooling_off_period": "#EC7211",
    "human_review_recommendation": "#7C6FE8",
}
PROTECTION_LABELS = {
    "no_action": "No action",
    "education_prompt": "Education prompt",
    "soft_friction": "Soft friction",
    "cooling_off_period": "Cooling-off period",
    "human_review_recommendation": "Human review",
}


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
        .section-caption {
            color: #5f6b85;
            font-size: 0.98rem;
            margin: -0.2rem 0 1.1rem 0;
            max-width: 820px;
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
    return build_monitoring_snapshot(
        db_path=prepared_db_path,
        require_batch_scores=False,
    )


@st.cache_data(show_spinner=False)
def cached_pricing_scenario_run(db_path: str) -> PricingScenarioRun:
    prepared_db_path = ensure_demo_database(Path(db_path))
    return build_pricing_scenario_run(db_path=prepared_db_path)


@st.cache_data(show_spinner=False)
def cached_decision_pack(db_path: str) -> tuple[list[str], str, bytes]:
    """Build the responsible-growth decision pack once per dataset.

    Returns (impact statements, HTML report, Excel bytes). Cached because assembling
    the report -- especially serialising the Excel workbook -- is the most expensive
    per-render work on the Customer outcomes tab.
    """
    data = cached_dashboard_data(db_path)
    report = build_report(
        feature_name="personalised_onboarding_pot_prompt",
        release_decision=onboarding_release_decision(
            data.experiment_variants, data.experiment_segment_outcomes
        ),
        customer_outcomes=data.customer_outcomes,
        onboarding_funnel=data.onboarding_funnel,
        fair_value=offer_fair_value(data.pricing_recommendations),
        protection_events=data.protection_events,
    )
    return report.summary.impact_statements, render_html(report), report_excel_bytes(report)


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


def _section_caption(text: str) -> None:
    st.markdown(f"<p class='section-caption'>{text}</p>", unsafe_allow_html=True)


def _render_product_health(data: DashboardData) -> None:
    _section_caption(
        "Executive product readout across activation, engagement, retention, adoption, and value."
    )
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
    _section_caption(
        "Experiment readouts focus on decision metrics, incrementality, "
        "unit economics, and guardrails."
    )
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


def _render_pricing_scenarios(run: PricingScenarioRun) -> None:
    summary = run.executive_summary
    cols = st.columns(4)
    cols[0].metric("Scenario runs", f"{int(summary['scenario_count']):,}")
    cols[1].metric("Ship candidates", f"{int(summary['ship_count']):,}")
    cols[2].metric("Best incentive", _gbp(float(summary["best_incentive_gbp"])))
    cols[3].metric("Best margin", _gbp(float(summary["best_expected_margin_gbp"])))

    scenario_frame = pd.DataFrame([row.__dict__ for row in run.scenarios])
    sensitivity_frame = pd.DataFrame([row.__dict__ for row in run.sensitivity_rows])
    if scenario_frame.empty:
        return

    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Scenario Portfolio")
        top_scenarios = scenario_frame.sort_values(
            ["expected_monthly_margin_gbp", "incremental_activated_customers"],
            ascending=False,
        ).head(8)
        st.dataframe(
            top_scenarios[
                [
                    "segment",
                    "proposed_incentive_gbp",
                    "projected_lift_pp",
                    "incremental_activated_customers",
                    "expected_monthly_margin_gbp",
                    "recommendation",
                ]
            ],
            width="stretch",
            hide_index=True,
        )
    with right:
        st.subheader("Sensitivity Check")
        best_scenario_id = str(summary["best_scenario_id"])
        best_sensitivity = sensitivity_frame[
            sensitivity_frame["scenario_id"] == best_scenario_id
        ].copy()
        if not best_sensitivity.empty:
            fig = px.bar(
                best_sensitivity,
                x="sensitivity_case",
                y="expected_monthly_margin_gbp",
                color="recommendation",
                color_discrete_map={
                    "ship": "#00A88F",
                    "iterate": "#F2B544",
                    "hold": "#EF4444",
                },
                labels={
                    "sensitivity_case": "Case",
                    "expected_monthly_margin_gbp": "Expected margin",
                    "recommendation": "Recommendation",
                },
            )
            _apply_chart_layout(fig, height=285)
            st.plotly_chart(fig, width="stretch")


def _render_pricing(data: DashboardData, scenario_run: PricingScenarioRun) -> None:
    _section_caption(
        "Pricing intelligence combines observed offer economics with scenario "
        "simulation and guardrails."
    )
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

    st.subheader("Scenario Runs")
    _render_pricing_scenarios(scenario_run)

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

    st.subheader("Fair-Value Governance")
    _section_caption(
        "Fairness lens on the commercial recommendation: an attractive offer is "
        "downgraded when its complaint, support, or human-review load points to poor "
        "customer value."
    )
    fair_value = offer_fair_value(data.pricing_recommendations)
    if fair_value.empty:
        st.info("No offers available for fair-value governance.")
        return
    downgrades = int(fair_value["downgraded"].sum())
    if downgrades:
        st.warning(
            f"{downgrades} offer(s) downgraded from scale on fair-value grounds."
        )
    fig = px.bar(
        fair_value,
        x="fair_value_score",
        y="offer_id",
        orientation="h",
        color="governance_action",
        color_discrete_map=GOVERNANCE_COLORS,
        labels={
            "fair_value_score": "Fair-value score",
            "offer_id": "Offer",
            "governance_action": "Governance action",
        },
        hover_data=["recommended_action", "reason", "exposures"],
    )
    _apply_chart_layout(fig, height=320)
    fig.update_xaxes(range=[0, 1])
    st.plotly_chart(fig, width="stretch")
    st.dataframe(
        fair_value[
            [
                "offer_id",
                "fair_value_score",
                "recommended_action",
                "governance_action",
                "reason",
            ]
        ],
        width="stretch",
        hide_index=True,
    )


def _render_release_verdict(data: DashboardData) -> None:
    decision = onboarding_release_decision(
        data.experiment_variants, data.experiment_segment_outcomes
    )
    if decision is None:
        return
    color = DECISION_COLORS.get(decision.decision, PRIMARY_BLUE)
    label = DECISION_LABELS.get(decision.decision, decision.decision.upper())
    st.markdown(
        f"""
        <div style="border-left: 6px solid {color}; background: #F8FAFC;
                    padding: 0.9rem 1.1rem; border-radius: 6px; margin-bottom: 1rem;">
            <div style="font-size: 0.85rem; color: #5f6b85;">
                Responsible release recommendation · {decision.feature_name}</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: {color};">{label}</div>
            <div style="font-size: 0.9rem; color: #5f6b85;">
                Evidence tier: {decision.evidence_tier}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for reason in decision.reasons:
        st.markdown(f"- {reason}")


def _render_decision_pack() -> None:
    """Offer the consolidated responsible-growth decision pack as HTML / Excel."""
    impact_statements, html_report, excel_bytes = cached_decision_pack(str(DEFAULT_DB_PATH))
    with st.expander("Responsible growth decision pack (download)"):
        for line in impact_statements:
            st.markdown(f"- {line}")
        left, right = st.columns(2)
        left.download_button(
            "Download HTML report",
            data=html_report,
            file_name="responsible_growth_report.html",
            mime="text/html",
        )
        right.download_button(
            "Download Excel pack",
            data=excel_bytes,
            file_name="responsible_growth_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def _render_customer_outcomes(data: DashboardData) -> None:
    _section_caption(
        "Customer outcomes and fairness: do growth decisions improve outcomes evenly, "
        "and is the onboarding change safe to ship?"
    )
    _render_release_verdict(data)
    _render_decision_pack()

    if data.customer_outcomes.empty:
        st.info("Customer-outcome marts are not available in this DuckDB build.")
        return

    gaps = customer_outcome_gaps(data.customer_outcomes)
    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Outcome Gaps By Segment")
        if gaps.empty:
            st.info("No segment had enough customers to estimate a stable gap.")
        else:
            display = gaps.assign(
                label=gaps["segment"] + " · " + gaps["outcome_label"]
            )
            fig = px.bar(
                display,
                x="gap_pp",
                y="label",
                orientation="h",
                color="outcome_label",
                color_discrete_map={
                    "D7 activation": PRIMARY_BLUE,
                    "Support contact": "#F2B544",
                    "Complaint": "#EF4444",
                },
                labels={
                    "gap_pp": "Disparity (pp)",
                    "label": "Segment · outcome",
                    "outcome_label": "Outcome",
                },
            )
            _apply_chart_layout(fig, height=340)
            st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader("D7 Activation By Digital Confidence")
        from src.wellbeing.metrics import segment_outcome_rates

        rates = segment_outcome_rates(
            data.customer_outcomes,
            "digital_confidence_band",
            ["activated_d7", "has_support_contact"],
            min_segment_size=30,
        )
        if rates.empty:
            st.info("Not enough customers per band to summarise.")
        else:
            fig = px.bar(
                rates,
                x="level",
                y="activated_d7",
                color="level",
                color_discrete_map={
                    "low": "#EF4444",
                    "medium": "#F2B544",
                    "high": "#00A88F",
                },
                labels={"level": "Digital confidence", "activated_d7": "D7 activation"},
                hover_data=["customers", "has_support_contact"],
            )
            _apply_chart_layout(fig, height=340)
            fig.update_layout(showlegend=False)
            fig.update_yaxes(tickformat=".0%")
            st.plotly_chart(fig, width="stretch")

    st.caption(
        "Wellbeing and vulnerability fields are synthetic proxies for evaluating "
        "product decisions. They must not be used for credit, pricing-penalty, or "
        "service-denial decisions."
    )


def _render_digital_inclusion(data: DashboardData) -> None:
    _section_caption(
        "Digital inclusion: who drops out of onboarding, which segments are "
        "underserved, and who should be offered an assisted journey."
    )
    if data.onboarding_funnel.empty:
        st.info("Onboarding-funnel marts are not available in this DuckDB build.")
        return

    funnel = onboarding_funnel_steps(data.onboarding_funnel)
    completion = float(
        data.onboarding_funnel["completed_onboarding"].astype(float).mean()
    )
    assisted = int(data.onboarding_funnel["needs_assisted_onboarding"].astype(bool).sum())
    cols = st.columns(3)
    cols[0].metric("Onboarding completion", _pct(completion))
    cols[1].metric("Customers", f"{len(data.onboarding_funnel):,}")
    cols[2].metric("Assisted-onboarding need", f"{assisted:,}")

    left, right = st.columns([1, 1.1])
    with left:
        st.subheader("Onboarding Funnel")
        fig = px.funnel(
            funnel,
            x="reached",
            y="label",
            labels={"reached": "Customers", "label": "Step"},
        )
        fig.update_traces(marker_color=PRIMARY_BLUE)
        _apply_chart_layout(fig, height=340)
        st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader("Abandonment By Digital Confidence")
        abandonment = onboarding_abandonment_by_segment(
            data.onboarding_funnel, "digital_confidence_band", min_segment_size=30
        )
        if abandonment.empty:
            st.info("Not enough customers per band to summarise.")
        else:
            fig = px.bar(
                abandonment,
                x="level",
                y="abandonment_rate",
                color="level",
                color_discrete_map={
                    "low": "#EF4444",
                    "medium": "#F2B544",
                    "high": "#00A88F",
                },
                labels={
                    "level": "Digital confidence",
                    "abandonment_rate": "Onboarding abandonment",
                },
                hover_data=["customers", "assisted_need_rate"],
            )
            _apply_chart_layout(fig, height=340)
            fig.update_layout(showlegend=False)
            fig.update_yaxes(tickformat=".0%")
            st.plotly_chart(fig, width="stretch")

    from src.inclusion import assisted_onboarding_segments

    flags: list = []
    for segment in ["digital_confidence_band", "income_band"]:
        if segment in data.onboarding_funnel.columns:
            flags.extend(
                assisted_onboarding_segments(data.onboarding_funnel, segment)
            )
    if flags:
        lines = ", ".join(
            f"{flag.segment}={flag.level} ({flag.abandonment_rate:.0%} abandon)"
            for flag in flags
        )
        st.warning(f"Assisted-onboarding candidates: {lines}")
    st.caption(
        "Inclusion proxies are synthetic and are used only to target supportive "
        "interventions, never to deny or restrict access."
    )


def _render_customer_protection(data: DashboardData) -> None:
    _section_caption(
        "Customer protection: risk-triggered support and education on transfers. Every "
        "response is supportive (education, soft friction, cooling-off, human review) - "
        "this is not a fraud engine and never blocks a payment."
    )
    if data.protection_events.empty:
        st.info("Customer-protection event marts are not available in this DuckDB build.")
        return

    summary = protection_intervention_summary(data.protection_events)
    total = len(data.protection_events)
    intervened = int(summary.loc[summary["action"] != "no_action", "events"].sum())
    cols = st.columns(3)
    cols[0].metric("Transfer events", f"{total:,}")
    cols[1].metric("Supportive interventions", f"{intervened:,}")
    cols[2].metric("Intervention rate", _pct(intervened / total if total else 0.0))

    summary = summary.assign(label=summary["action"].map(PROTECTION_LABELS))
    fig = px.bar(
        summary,
        x="events",
        y="label",
        orientation="h",
        color="action",
        color_discrete_map=PROTECTION_COLORS,
        labels={"events": "Events", "label": "Intervention", "action": "Intervention"},
        category_orders={"label": [PROTECTION_LABELS[a] for a in summary["action"]]},
    )
    _apply_chart_layout(fig, height=320)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(
        summary[["label", "events", "share"]].rename(
            columns={"label": "Intervention", "events": "Events", "share": "Share"}
        ),
        width="stretch",
        hide_index=True,
    )
    st.caption(
        "A responsible-intervention simulation on synthetic data. It models support "
        "and education, not automated fraud blocking."
    )


def _render_monitoring(snapshot: MonitoringSnapshot) -> None:
    _section_caption(
        "Operational checks show whether the dashboard, scoring workflow, and "
        "supporting artifacts are ready for a reviewer walkthrough."
    )
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
    st.title("Responsible Neobank Growth Platform")

    db_path = str(DEFAULT_DB_PATH)

    try:
        data = cached_dashboard_data(db_path)
        monitoring_snapshot = cached_monitoring_snapshot(db_path)
        pricing_scenario_run = cached_pricing_scenario_run(db_path)
    except Exception as exc:  # pragma: no cover - Streamlit-only failure path.
        st.error(str(exc))
        st.stop()

    _metric_grid(data)
    # Dynamic tabs (on_change="rerun"): only the open tab's content renders, so the
    # other six tabs -- including the decision-pack build -- don't recompute on every
    # rerun. tab.open is True only for the selected tab.
    (
        product_tab,
        outcomes_tab,
        inclusion_tab,
        protection_tab,
        pricing_tab,
        experiment_tab,
        monitoring_tab,
    ) = st.tabs(
        [
            "Product health",
            "Customer outcomes",
            "Digital inclusion",
            "Customer protection",
            "Pricing intelligence",
            "Experiments",
            "Monitoring",
        ],
        on_change="rerun",
    )
    if product_tab.open:
        with product_tab:
            _render_product_health(data)
    if outcomes_tab.open:
        with outcomes_tab:
            _render_customer_outcomes(data)
    if inclusion_tab.open:
        with inclusion_tab:
            _render_digital_inclusion(data)
    if protection_tab.open:
        with protection_tab:
            _render_customer_protection(data)
    if pricing_tab.open:
        with pricing_tab:
            _render_pricing(data, pricing_scenario_run)
    if experiment_tab.open:
        with experiment_tab:
            _render_experiments(data)
    if monitoring_tab.open:
        with monitoring_tab:
            _render_monitoring(monitoring_snapshot)


if __name__ == "__main__":
    main()
