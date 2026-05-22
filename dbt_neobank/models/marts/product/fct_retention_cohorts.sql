with activated_users as (
    select
        user_id,
        signup_week
    from {{ ref('fct_activation') }}
    where activated_ever
),

weekly_activity as (
    select
        activated_users.signup_week,
        date_diff('week', activated_users.signup_week, activity.activity_week) as weeks_since_signup,
        activated_users.user_id
    from activated_users
    inner join {{ ref('int_user_weekly_activity') }} as activity
        on activated_users.user_id = activity.user_id
    where date_diff('week', activated_users.signup_week, activity.activity_week) between 0 and 12
),

cohort_sizes as (
    select
        signup_week,
        count(*) as activated_users
    from activated_users
    group by 1
)

select
    weekly_activity.signup_week,
    weekly_activity.weeks_since_signup,
    cohort_sizes.activated_users,
    count(distinct weekly_activity.user_id) as retained_users,
    count(distinct weekly_activity.user_id)::double / cohort_sizes.activated_users as retention_rate
from weekly_activity
inner join cohort_sizes
    on weekly_activity.signup_week = cohort_sizes.signup_week
group by 1, 2, 3
