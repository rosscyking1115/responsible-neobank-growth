select
    user_id,
    min(occurred_at) as first_transaction_ts,
    min(occurred_date) as first_transaction_date,
    count(*) as lifetime_transaction_count,
    sum(amount_gbp) as lifetime_card_spend_gbp,
    sum(interchange_revenue_gbp) as lifetime_interchange_revenue_gbp
from {{ ref('stg_transactions') }}
where is_card_transaction
group by 1
