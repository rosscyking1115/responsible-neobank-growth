select
    feature_name,
    date_trunc('month', event_date)::date as adoption_month,
    count(distinct user_id) as adopting_users,
    count(*) as adoption_events
from {{ ref('stg_feature_events') }}
where event_type = 'adopted'
group by 1, 2
