select
    region,
    cast(date as date) as date_day,
    cast(signups as {{ integer_type() }}) as signups,
    cast(treated_region as boolean) as treated_region,
    cast(post_period as boolean) as post_period,
    cast(incentive_active as boolean) as incentive_active
from {{ raw_table('region_daily_signups', 'region_daily_signups.parquet') }}
