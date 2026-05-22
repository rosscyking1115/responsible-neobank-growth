import marimo

__generated_with = "0.23.7"
app = marimo.App(width="full")


@app.cell
def _():
    from pathlib import Path

    import altair as alt
    import duckdb
    import marimo as mo
    import pandas as pd

    alt.data_transformers.disable_max_rows()
    return Path, alt, duckdb, mo, pd


@app.cell
def _(mo):
    mo.md("""
    # EDA: Activation Drivers and Product Opportunities

    Audience: a Monzo-style Product Manager looking for the next activation and retention bets.

    This notebook reads from the dbt metrics layer in `neobank.duckdb`. Before opening it, run:

    ```powershell
    uv run python -m data_generator.generate --users 50000 --months 12 --seed 42 --output-dir raw/phase1_full
    uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank --vars "{raw_path: raw/phase1_full}"
    uv run marimo edit notebooks/01_eda_activation_drivers.py
    ```
    """)
    return


@app.cell
def _(Path, duckdb, mo, pd):
    db_path = Path("neobank.duckdb")

    def query(sql: str) -> pd.DataFrame:
        if not db_path.exists():
            raise FileNotFoundError(
                "neobank.duckdb not found. Generate data and run dbt build before opening this notebook."
            )
        with duckdb.connect(str(db_path), read_only=True) as connection:
            return connection.execute(sql).fetchdf()

    mo.md(
        f"""
        **Data source:** `{db_path}`  
        **Notebook contract:** each chart is backed by a dbt mart or intermediate table.
        """
    )
    return (query,)


@app.cell
def _(query):
    activation_by_speed_df = query(
        """
        with users as (
            select
                user_id,
                signup_week,
                case
                    when first_transaction_ts is null then 'no activation'
                    when first_transaction_ts <= signup_ts + interval 1 day then 'D1 active'
                    when first_transaction_ts <= signup_ts + interval 7 day then 'D2-7 active'
                    else 'late active'
                end as activation_speed
            from main_marts.fct_activation
        ),

        week_4_activity as (
            select distinct
                users.user_id
            from users
            inner join main_intermediate.int_user_weekly_activity as activity
                on users.user_id = activity.user_id
            where date_diff('week', users.signup_week, activity.activity_week) = 4
        )

        select
            users.activation_speed,
            count(*) as users,
            count(week_4_activity.user_id) as retained_w4_users,
            count(week_4_activity.user_id)::double / count(*) as w4_retention_rate
        from users
        left join week_4_activity
            on users.user_id = week_4_activity.user_id
        group by 1
        order by
            case users.activation_speed
                when 'D1 active' then 1
                when 'D2-7 active' then 2
                when 'late active' then 3
                else 4
            end
        """
    )
    return (activation_by_speed_df,)


@app.cell
def _(activation_by_speed_df, alt, mo):
    activation_speed_chart = (
        alt.Chart(activation_by_speed_df)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("activation_speed:N", title="Activation behaviour", sort=None),
            y=alt.Y("w4_retention_rate:Q", title="W4 retention", axis=alt.Axis(format="%")),
            color=alt.Color("activation_speed:N", legend=None),
            tooltip=[
                "activation_speed",
                alt.Tooltip("users:Q", format=","),
                alt.Tooltip("w4_retention_rate:Q", format=".1%"),
            ],
        )
        .properties(height=320)
    )
    mo.vstack(
        [
            mo.md("## 1. Which onboarding behaviours predict W4 retention?"),
            activation_speed_chart,
            mo.md(
                """
                **Caption:** W4 retention by first-transaction timing.

                **Insight:** Users who transact on D1 retain materially better than later activators;
                users who activate after D7 are still worth saving, but they behave more like a recovery
                segment than a normal onboarding cohort.

                **So what:** Prioritise nudges that move users from D2-7 into D1, then use a separate
                recovery journey for late activators instead of treating all unactivated users the same.
                """
            ),
        ]
    )
    return


@app.cell
def _(query):
    pot_engagement_df = query(
        """
        with user_features as (
            select
                activation.user_id,
                activation.signup_channel,
                activation.income_segment,
                activation.lifetime_transaction_count,
                activation.lifetime_card_spend_gbp,
                max(case when features.feature_name = 'savings_pot' then 1 else 0 end) as adopted_pot
            from main_marts.fct_activation as activation
            left join main_staging.stg_feature_events as features
                on activation.user_id = features.user_id
            where activation.activated_ever
            group by 1, 2, 3, 4, 5
        ),

        matched_segments as (
            select
                signup_channel,
                income_segment
            from user_features
            group by 1, 2
            having min(adopted_pot) = 0 and max(adopted_pot) = 1
        )

        select
            case when user_features.adopted_pot = 1 then 'Pot adopter' else 'Matched non-adopter' end
                as segment,
            count(*) as users,
            avg(user_features.lifetime_transaction_count) as avg_transactions,
            avg(user_features.lifetime_card_spend_gbp) as avg_card_spend_gbp
        from user_features
        inner join matched_segments
            on user_features.signup_channel = matched_segments.signup_channel
            and user_features.income_segment = matched_segments.income_segment
        group by 1
        order by 1
        """
    )
    return (pot_engagement_df,)


@app.cell
def _(alt, mo, pot_engagement_df):
    pot_engagement_chart = (
        alt.Chart(pot_engagement_df)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("segment:N", title="Matched segment", sort=None),
            y=alt.Y("avg_transactions:Q", title="Average lifetime transactions"),
            color=alt.Color("segment:N", legend=None),
            tooltip=[
                "segment",
                alt.Tooltip("users:Q", format=","),
                alt.Tooltip("avg_transactions:Q", format=".1f"),
                alt.Tooltip("avg_card_spend_gbp:Q", format=",.0f"),
            ],
        )
        .properties(height=320)
    )
    mo.vstack(
        [
            mo.md("## 2. Do Savings Pots increase engagement?"),
            pot_engagement_chart,
            mo.md(
                """
                **Caption:** Pot adopters versus non-adopters matched on signup channel and income segment.

                **Insight:** Pot adopters transact more often than comparable non-adopters, which is a
                promising product signal but not yet a causal claim.

                **So what:** Treat Pots as a strong candidate for an onboarding experiment, not as proof
                of product lift. The Phase 4 A/B test should measure whether prompting Pot setup moves
                activation and retention without increasing support load.
                """
            ),
        ]
    )
    return


@app.cell
def _(query):
    salary_activation_df = query(
        """
        with salary_users as (
            select distinct user_id
            from main_staging.stg_feature_events
            where feature_name = 'salary_sorter'
        )

        select
            case when salary_users.user_id is not null then 'Salary detected' else 'No salary signal' end
                as salary_segment,
            count(*) as users,
            avg(activated_d7::integer) as d7_activation_rate,
            avg(activated_ever::integer) as ever_activation_rate
        from main_marts.fct_activation as activation
        left join salary_users
            on activation.user_id = salary_users.user_id
        group by 1
        order by 1
        """
    )
    return (salary_activation_df,)


@app.cell
def _(alt, mo, salary_activation_df):
    salary_activation_chart = (
        alt.Chart(salary_activation_df)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("salary_segment:N", title="Salary signal", sort=None),
            y=alt.Y("d7_activation_rate:Q", title="D7 activation", axis=alt.Axis(format="%")),
            color=alt.Color("salary_segment:N", legend=None),
            tooltip=[
                "salary_segment",
                alt.Tooltip("users:Q", format=","),
                alt.Tooltip("d7_activation_rate:Q", format=".1%"),
                alt.Tooltip("ever_activation_rate:Q", format=".1%"),
            ],
        )
        .properties(height=320)
    )
    mo.vstack(
        [
            mo.md("## 3. Are users with salary signals more likely to activate?"),
            salary_activation_chart,
            mo.md(
                """
                **Caption:** Activation rates for users with and without Salary Sorter adoption.

                **Insight:** Salary-linked users are substantially more committed, but salary adoption
                happens after signup for many users, so this is more of a primary-banking signal than an
                early acquisition feature.

                **So what:** Build a primary-banking KPI path in the dashboard: activation is the first
                milestone, but salary behaviour is a deeper engagement marker that should influence CLV
                and retention reads.
                """
            ),
        ]
    )
    return


@app.cell
def _(query):
    cohort_channel_df = query(
        """
        select
            signup_week,
            signup_channel,
            count(*) as users,
            avg(activated_d7::integer) as d7_activation_rate
        from main_marts.fct_activation
        group by 1, 2
        having count(*) >= 20
        """
    )
    worst_channel_df = query(
        """
        select
            signup_channel,
            count(*) as users,
            avg(activated_d7::integer) as d7_activation_rate
        from main_marts.fct_activation
        group by 1
        order by d7_activation_rate asc
        limit 1
        """
    )
    return cohort_channel_df, worst_channel_df


@app.cell
def _(alt, cohort_channel_df, mo, worst_channel_df):
    cohort_heatmap = (
        alt.Chart(cohort_channel_df)
        .mark_rect()
        .encode(
            x=alt.X("yearmonthdate(signup_week):O", title="Signup week"),
            y=alt.Y("signup_channel:N", title="Signup channel"),
            color=alt.Color(
                "d7_activation_rate:Q",
                title="D7 activation",
                scale=alt.Scale(scheme="tealblues"),
            ),
            tooltip=[
                "signup_channel",
                alt.Tooltip("signup_week:T", title="Signup week"),
                alt.Tooltip("users:Q", format=","),
                alt.Tooltip("d7_activation_rate:Q", format=".1%"),
            ],
        )
        .properties(height=320)
    )
    worst_channel = worst_channel_df.iloc[0]["signup_channel"]
    worst_rate = worst_channel_df.iloc[0]["d7_activation_rate"]
    mo.vstack(
        [
            mo.md("## 4. Which acquisition cohort has the lowest activation?"),
            cohort_heatmap,
            mo.md(
                f"""
                **Caption:** Weekly D7 activation heatmap by signup channel.

                **Insight:** The weakest overall channel is `{worst_channel}` with D7 activation of
                `{worst_rate:.1%}` in this generated population.

                **So what:** Do not optimise onboarding only at the aggregate level. Paid or partnership
                cohorts can hide low-intent users who need different messaging, qualification, or budget
                allocation decisions.
                """
            ),
        ]
    )
    return


@app.cell
def _(query):
    churn_risk_df = query(
        """
        with adoption_depth as (
            select
                activation.user_id,
                count(distinct features.feature_name) as adopted_features
            from main_marts.fct_activation as activation
            left join main_staging.stg_feature_events as features
                on activation.user_id = features.user_id
            where activation.activated_ever
            group by 1
        ),

        week_activity as (
            select
                adoption_depth.user_id,
                case
                    when adoption_depth.adopted_features >= 3 then '3+ features'
                    when adoption_depth.adopted_features = 2 then '2 features'
                    when adoption_depth.adopted_features = 1 then '1 feature'
                    else '0 features'
                end as feature_depth,
                max(case when date_diff('week', activation.signup_week, activity.activity_week) = 4 then 1 else 0 end)
                    as retained_w4
            from adoption_depth
            inner join main_marts.fct_activation as activation
                on adoption_depth.user_id = activation.user_id
            left join main_intermediate.int_user_weekly_activity as activity
                on adoption_depth.user_id = activity.user_id
            group by 1, 2
        )

        select
            feature_depth,
            count(*) as users,
            avg(retained_w4) as w4_retention_rate,
            1 - avg(retained_w4) as first_month_churn_risk
        from week_activity
        group by 1
        order by
            case feature_depth
                when '0 features' then 1
                when '1 feature' then 2
                when '2 features' then 3
                else 4
            end
        """
    )
    return (churn_risk_df,)


@app.cell
def _(alt, churn_risk_df, mo):
    churn_risk_chart = (
        alt.Chart(churn_risk_df)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("feature_depth:N", title="Adoption depth", sort=None),
            y=alt.Y("first_month_churn_risk:Q", title="First-month churn risk", axis=alt.Axis(format="%")),
            tooltip=[
                "feature_depth",
                alt.Tooltip("users:Q", format=","),
                alt.Tooltip("w4_retention_rate:Q", format=".1%"),
                alt.Tooltip("first_month_churn_risk:Q", format=".1%"),
            ],
        )
        .properties(height=320)
    )
    mo.vstack(
        [
            mo.md("## 5. Which users are likely to churn after the first month?"),
            churn_risk_chart,
            mo.md(
                """
                **Caption:** First-month churn risk by number of adopted product features.

                **Insight:** Feature depth is a clean retention proxy: users with no adopted features
                have the highest first-month churn risk, while multi-feature users look meaningfully
                stickier.

                **So what:** The activation model should not just predict risk; it should support a
                decision about which low-depth users can be nudged toward customer-good outcomes without
                creating support burden or unfair treatment.
                """
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## Product Readout

    1. D1 transaction is the strongest early retention marker in this synthetic population.
    2. Pots are a credible experiment candidate, but the observational adoption gap is not causal.
    3. Salary behaviour should sit in the primary-banking/CLV story rather than the first-touch
       acquisition story.
    4. Channel-level cohort views are necessary because aggregate activation can hide low-intent
       acquisition pockets.
    5. Feature depth is a practical churn-risk signal and should feed Phase 5 decisioning.

    **Recommended next analysis:** move from observational EDA into the Phase 4 onboarding A/B test,
    using D7 activation as the primary metric and support/contact burden as a guardrail.
    """)
    return


if __name__ == "__main__":
    app.run()
