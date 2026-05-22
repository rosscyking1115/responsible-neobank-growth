select
    user_id,
    date_trunc('week', occurred_date)::date as activity_week,
    count(*) as transactions,
    sum(amount_gbp) as card_spend_gbp,
    sum(interchange_revenue_gbp) as interchange_revenue_gbp
from {{ ref('stg_transactions') }}
group by 1, 2
