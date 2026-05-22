select
    activity_week,
    count(distinct user_id) as weekly_active_users,
    sum(transactions) as transactions,
    sum(card_spend_gbp) as card_spend_gbp,
    avg(transactions) as transactions_per_active_user
from {{ ref('int_user_weekly_activity') }}
group by 1
