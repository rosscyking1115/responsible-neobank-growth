select
    region,
    cast(date as date) as date_day,
    cast(signups as integer) as signups,
    cast(treated_region as boolean) as treated_region,
    cast(post_period as boolean) as post_period,
    cast(incentive_active as boolean) as incentive_active
from read_parquet('{{ var("raw_path", "raw/ci") }}/region_daily_signups.parquet')
