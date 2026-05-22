select
    user_id,
    signup_ts,
    first_transaction_ts
from {{ ref('fct_activation') }}
where first_transaction_ts < signup_ts
