select
    users.user_id,
    users.signup_ts,
    users.signup_date,
    {{ date_trunc_day('week', 'users.signup_date') }} as signup_week,
    users.region,
    users.signup_channel,
    users.device_os,
    users.age,
    users.income_segment,
    users.push_opt_in,
    users.vulnerable_customer_flag,
    users.business_account_flag,
    first_tx.first_transaction_ts,
    first_tx.first_transaction_date,
    first_tx.lifetime_transaction_count,
    first_tx.lifetime_card_spend_gbp,
    first_tx.lifetime_interchange_revenue_gbp,
    first_tx.first_transaction_ts is not null as activated_ever,
    first_tx.first_transaction_ts <= {{ timestamp_add_days('users.signup_ts', 7) }} as activated_d7
from {{ ref('stg_users') }} as users
left join {{ ref('int_user_first_transaction') }} as first_tx
    on users.user_id = first_tx.user_id
