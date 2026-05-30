select
    referral_id,
    referrer_user_id,
    referee_user_id,
    cast(created_at as timestamp) as created_at,
    cast(created_date as date) as created_date,
    referrer_region,
    referee_region,
    cast(incentive_region_treated as boolean) as incentive_region_treated,
    cast(incentive_active as boolean) as incentive_active,
    cast(is_incremental_ground_truth as boolean) as is_incremental_ground_truth,
    cast(referrer_reward_gbp as {{ float_type() }}) as referrer_reward_gbp,
    cast(referee_reward_gbp as {{ float_type() }}) as referee_reward_gbp
from {{ raw_table('referrals', 'referrals.parquet') }}
