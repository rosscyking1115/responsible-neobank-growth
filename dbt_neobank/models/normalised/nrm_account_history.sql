-- Account state intervals derived from canonical events, ordered by business
-- occurrence time (never ingestion time): activated -> funded.
with states as (
    select
        account_id,
        customer_id,
        case event_type
            when 'account_activated' then 'activated'
            when 'account_funded' then 'funded'
        end as state,
        occurred_at as valid_from,
        event_id
    from {{ ref('nrm_account_event') }}
)

select
    account_id,
    customer_id,
    state,
    valid_from,
    lead(valid_from) over (
        partition by account_id order by valid_from, event_id
    ) as valid_to,
    lead(valid_from) over (
        partition by account_id order by valid_from, event_id
    ) is null as is_current
from states
