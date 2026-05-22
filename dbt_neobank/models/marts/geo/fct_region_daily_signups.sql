select
    region,
    date_day,
    signups,
    treated_region,
    post_period,
    incentive_active
from {{ ref('stg_region_daily_signups') }}
