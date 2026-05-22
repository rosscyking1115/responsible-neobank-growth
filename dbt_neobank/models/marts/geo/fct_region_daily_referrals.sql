with region_days as (
    select
        region,
        date_day,
        treated_region,
        post_period,
        incentive_active,
        signups
    from {{ ref('fct_region_daily_signups') }}
),

referrals as (
    select
        referee_region as region,
        created_date as date_day,
        count(*) as referral_signups,
        sum(case when is_incremental_ground_truth then 1 else 0 end) as incremental_signups_ground_truth,
        sum(referrer_reward_gbp + referee_reward_gbp) as reward_cost_gbp
    from {{ ref('stg_referrals') }}
    group by 1, 2
)

select
    region_days.region,
    region_days.date_day,
    region_days.treated_region,
    region_days.post_period,
    region_days.incentive_active,
    region_days.signups,
    coalesce(referrals.referral_signups, 0) as referral_signups,
    coalesce(referrals.incremental_signups_ground_truth, 0) as incremental_signups_ground_truth,
    coalesce(referrals.reward_cost_gbp, 0.0) as reward_cost_gbp
from region_days
left join referrals
    on
        region_days.region = referrals.region
        and region_days.date_day = referrals.date_day
