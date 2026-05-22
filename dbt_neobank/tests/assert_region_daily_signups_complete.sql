select
    region,
    date_day
from {{ ref('fct_region_daily_signups') }}
group by 1, 2
having count(*) != 1
