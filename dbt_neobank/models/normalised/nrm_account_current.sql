-- Current state per account (single row), plus first-funding facts.
with current_state as (
    select account_id, customer_id, state as current_state, valid_from as state_since
    from {{ ref('nrm_account_history') }}
    where is_current
),

first_funding as (
    select
        account_id,
        min(occurred_at) as first_funded_at,
        min_by(amount_minor, occurred_at) as first_funding_amount_minor
    from {{ ref('nrm_account_event') }}
    where event_type = 'account_funded' and is_first_funding
    group by account_id
)

select
    current_state.account_id,
    current_state.customer_id,
    current_state.current_state,
    current_state.state_since,
    first_funding.first_funded_at,
    first_funding.first_funding_amount_minor
from current_state
left join first_funding on current_state.account_id = first_funding.account_id
