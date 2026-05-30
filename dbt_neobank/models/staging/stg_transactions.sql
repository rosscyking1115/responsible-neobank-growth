select
    transaction_id,
    user_id,
    cast(occurred_at as timestamp) as occurred_at,
    cast(occurred_date as date) as occurred_date,
    region,
    merchant_category,
    cast(amount_gbp as {{ float_type() }}) as amount_gbp,
    cast(is_card_transaction as boolean) as is_card_transaction,
    cast(interchange_revenue_gbp as {{ float_type() }}) as interchange_revenue_gbp
from {{ raw_table('transactions', 'transactions.parquet') }}
