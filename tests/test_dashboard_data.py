from pathlib import Path

import duckdb
import pytest

from app.dashboard_data import (
    ensure_demo_database,
    load_dashboard_data,
    onboarding_lift_pp,
    pricing_economics,
    pricing_margin_by_offer,
    referral_economics,
    referral_grouped_daily,
    trim_partial_week,
)


def _build_dashboard_fixture(db_path: Path) -> None:
    with duckdb.connect(str(db_path)) as con:
        con.execute("create schema main_marts")
        con.execute(
            """
            create table main_marts.fct_activation as
            select *
            from (
                values
                    (1, date '2026-01-01', 'London', 'organic', true, true, 4, 120.0),
                    (2, date '2026-01-02', 'London', 'paid', false, true, 2, 40.0),
                    (3, date '2026-01-03', 'Wales', 'organic', true, true, 5, 160.0)
            ) as t(
                user_id,
                signup_date,
                region,
                signup_channel,
                activated_d7,
                activated_ever,
                lifetime_transaction_count,
                lifetime_card_spend_gbp
            )
            """
        )
        con.execute(
            """
            create table main_marts.fct_user_clv_proxy as
            select *
            from (
                values
                    (1, 'London', 'organic', 'mass', true, 32.0),
                    (2, 'London', 'paid', 'student', false, 12.0),
                    (3, 'Wales', 'organic', 'mass', true, 48.0)
            ) as t(
                user_id,
                region,
                signup_channel,
                income_segment,
                activated_d7,
                clv_proxy_12m_gbp
            )
            """
        )
        con.execute(
            """
            create table main_marts.fct_weekly_engagement as
            select *
            from (
                values
                    (date '2026-01-05', 2, 6, 180.0, 3.0),
                    (date '2026-01-12', 3, 8, 240.0, 2.7)
            ) as t(
                activity_week,
                weekly_active_users,
                transactions,
                card_spend_gbp,
                transactions_per_active_user
            )
            """
        )
        con.execute(
            """
            create table main_marts.fct_retention_cohorts as
            select *
            from (
                values
                    (date '2026-01-05', 0, 2, 2, 1.0),
                    (date '2026-01-05', 1, 2, 1, 0.5)
            ) as t(
                signup_week,
                weeks_since_signup,
                activated_users,
                retained_users,
                retention_rate
            )
            """
        )
        con.execute(
            """
            create table main_marts.fct_feature_adoption as
            select *
            from (
                values
                    ('savings_pot', date '2026-01-01', 2, 3),
                    ('salary_sorter', date '2026-01-01', 1, 1)
            ) as t(feature_name, adoption_month, adopting_users, adoption_events)
            """
        )
        con.execute(
            """
            create table main_marts.fct_experiment_user_metrics as
            select *
            from (
                values
                    ('personalised_onboarding_pot_prompt', 1, 'control', true, 0, 0, 0),
                    ('personalised_onboarding_pot_prompt', 2, 'control', false, 1, 0, 0),
                    ('personalised_onboarding_pot_prompt', 3, 'treatment', true, 0, 0, 1),
                    ('personalised_onboarding_pot_prompt', 4, 'treatment', true, 0, 0, 0)
            ) as t(
                experiment_name,
                user_id,
                variant,
                activated_d7,
                support_contacts,
                complaints,
                app_crashes
            )
            """
        )
        con.execute(
            """
            create table main_marts.fct_region_daily_referrals as
            select *
            from (
                values
                    ('London', date '2026-01-01', false, false, false, 10, 1, 0, 0.0),
                    ('Wales', date '2026-01-01', true, true, true, 12, 5, 2, 60.0),
                    ('Wales', date '2026-01-02', true, true, true, 9, 3, 1, 30.0)
            ) as t(
                region,
                date_day,
                treated_region,
                post_period,
                incentive_active,
                signups,
                referral_signups,
                incremental_signups_ground_truth,
                reward_cost_gbp
            )
            """
        )
        con.execute(
            """
            create table main_marts.fct_pricing_outcomes as
            select *
            from (
                values
                    (
                        'easy_access_savings_boost',
                        date '2026-01-01',
                        'London',
                        'standard',
                        10,
                        3,
                        2,
                        0.30,
                        18.0,
                        6.0,
                        12.0,
                        0.02,
                        0.01,
                        1
                    ),
                    (
                        'premium_bundle_trial',
                        date '2026-01-01',
                        'Wales',
                        'incentive',
                        5,
                        1,
                        1,
                        0.20,
                        7.0,
                        4.0,
                        3.0,
                        0.03,
                        0.00,
                        2
                    )
            ) as t(
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
            )
            """
        )
        con.execute(
            """
            create table main_marts.mart_pricing_recommendations as
            select *
            from (
                values
                    (
                        'easy_access_savings_boost',
                        'savings',
                        'rate_boost',
                        'student',
                        'standard',
                        10,
                        0.30,
                        1.20,
                        12.0,
                        0.02,
                        0.01,
                        0.10,
                        'scale',
                        'positive_margin_and_conversion'
                    ),
                    (
                        'premium_bundle_trial',
                        'subscription',
                        'fee_trial',
                        'middle',
                        'incentive',
                        5,
                        0.20,
                        0.60,
                        3.0,
                        0.03,
                        0.00,
                        0.40,
                        'human_review',
                        'customer_understanding_review'
                    )
            ) as t(
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
            )
            """
        )


def test_load_dashboard_data_summarises_marts(tmp_path: Path) -> None:
    db_path = tmp_path / "dashboard.duckdb"
    _build_dashboard_fixture(db_path)

    data = load_dashboard_data(db_path)

    assert int(data.overview["users"]) == 3
    assert data.weekly_engagement["weekly_active_users"].tolist() == [2, 3]
    assert data.activation_by_region.loc[0, "region"] == "London"
    assert data.retention_curve["weeks_since_signup"].tolist() == [1]
    assert data.pricing_recommendations["recommended_action"].tolist() == [
        "scale",
        "human_review",
    ]
    assert onboarding_lift_pp(data.experiment_variants) == 50.0


def test_ensure_demo_database_returns_existing_database(tmp_path: Path) -> None:
    db_path = tmp_path / "existing.duckdb"
    db_path.touch()

    prepared_path = ensure_demo_database(db_path)

    assert prepared_path == db_path


def test_ensure_demo_database_bootstraps_missing_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    db_path = tmp_path / "demo.duckdb"
    raw_path = tmp_path / "raw"

    def fake_run_bootstrap_command(
        command: list[str], *, env: dict[str, str] | None = None
    ) -> None:
        calls.append((command, env))

    monkeypatch.setattr(
        "app.dashboard_data._run_bootstrap_command",
        fake_run_bootstrap_command,
    )

    prepared_path = ensure_demo_database(db_path, raw_path=raw_path, users=10, months=1)

    assert prepared_path == db_path
    assert calls[0][0][-6:] == [
        "--users",
        "10",
        "--months",
        "1",
        "--output-dir",
        str(raw_path),
    ]
    assert calls[1][0][-2] == "--vars"
    assert calls[1][0][-1] == f"{{raw_path: '{raw_path.as_posix()}'}}"
    assert calls[1][1] is not None
    assert calls[1][1]["NEOBANK_DUCKDB_PATH"] == str(db_path)


def test_trim_partial_week_removes_final_incomplete_week(tmp_path: Path) -> None:
    db_path = tmp_path / "dashboard.duckdb"
    _build_dashboard_fixture(db_path)
    data = load_dashboard_data(db_path)
    weekly = data.weekly_engagement.copy()
    weekly.loc[len(weekly)] = ["2026-01-19", 1, 1, 10.0, 1.0]

    trimmed = trim_partial_week(weekly)

    assert trimmed["weekly_active_users"].tolist() == [2, 3]


def test_referral_helpers_compute_economics_and_groups(tmp_path: Path) -> None:
    db_path = tmp_path / "dashboard.duckdb"
    _build_dashboard_fixture(db_path)
    data = load_dashboard_data(db_path)

    economics = referral_economics(data.referral_daily)
    grouped = referral_grouped_daily(data.referral_daily)

    assert economics["treated_post_referral_signups"] == 8.0
    assert economics["reward_cost_gbp"] == 90.0
    assert economics["embedded_incremental_signups"] == 3.0
    assert economics["cost_per_embedded_incremental_signup"] == 30.0
    assert set(grouped["geo_group"]) == {"Control regions", "Treated regions"}


def test_pricing_helpers_compute_economics_and_offer_margin(tmp_path: Path) -> None:
    db_path = tmp_path / "dashboard.duckdb"
    _build_dashboard_fixture(db_path)
    data = load_dashboard_data(db_path)

    economics = pricing_economics(data.pricing_outcomes)
    margin = pricing_margin_by_offer(data.pricing_recommendations)

    assert economics["exposures"] == 15.0
    assert round(economics["acceptance_rate"], 4) == 0.2667
    assert economics["net_margin_30d_gbp"] == 15.0
    assert round(economics["human_review_rate"], 4) == 0.2
    assert margin.loc[0, "offer_id"] == "easy_access_savings_boost"
