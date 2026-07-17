-- Double-entry journal lines for the bounded referral-reward subledger
-- (docs/contracts/reward-reconciliation.md). Two lines per canonical reward
-- event over the three fictional accounts; not a claim about any real bank's
-- accounting policy.
with reward_events as (
    select *
    from {{ ref('nrm_reward_event') }}
),

entries as (
    select
        event_id,
        reward_id,
        referral_id,
        occurred_at,
        arrival_date,
        amount_minor,
        'debit' as entry_side,
        case event_type
            when 'reward_booked' then 'referral_reward_expense'
            when 'reward_settled' then 'referral_reward_payable'
            when 'reward_reversed' then 'referral_reward_payable'
        end as account
    from reward_events

    union all

    select
        event_id,
        reward_id,
        referral_id,
        occurred_at,
        arrival_date,
        amount_minor,
        'credit' as entry_side,
        case event_type
            when 'reward_booked' then 'referral_reward_payable'
            when 'reward_settled' then 'reward_cash_clearing'
            when 'reward_reversed' then 'referral_reward_expense'
        end as account
    from reward_events
)

select
    event_id || '_' || entry_side as ledger_entry_id,
    event_id,
    reward_id,
    referral_id,
    entry_side,
    account,
    amount_minor,
    occurred_at,
    arrival_date
from entries
