-- Compatibility view: fct_activation's core contract served from the governed
-- growth_acquisition interface. Grain preserved (one row per customer).
-- Declared differences (compatibility.yml): batch-universe attribute columns
-- (region, device, income, wellbeing flags) and lifetime monetary aggregates
-- are not served by the event boundary — they remain on the preserved batch
-- models until their own migration decision.
select
    customer_id as user_id,
    applied_at as signup_ts,
    cast(applied_at as date) as signup_date,
    cast({{ date_trunc_day('week', 'applied_at') }} as date) as signup_week,
    channel as signup_channel,
    first_funded_at as first_transaction_ts,
    cast(first_funded_at as date) as first_transaction_date,
    is_activated as activated_ever,
    coalesce(
        first_funded_at <= {{ ts_add_days('applied_at', 7) }},
        false
    ) as activated_d7
from {{ ref('prs_growth_acquisition') }}
