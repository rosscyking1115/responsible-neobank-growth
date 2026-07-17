{{ config(
    materialized='incremental',
    unique_key='ledger_entry_id',
    incremental_strategy=('merge' if target.type == 'bigquery' else 'delete+insert'),
    partition_by={'field': 'arrival_date', 'data_type': 'date', 'granularity': 'day'},
    cluster_by=['account'],
    labels={'project': 'neobank', 'layer': 'normalised'}
) }}

-- Double-entry journal lines for the bounded referral-reward subledger
-- (docs/contracts/reward-reconciliation.md). Two lines per canonical reward
-- event over the three fictional accounts; not a claim about any real bank's
-- accounting policy.
with reward_events as (
    select *
    from {{ ref('nrm_reward_event') }}
    where 1 = 1
        {#-
          Ledger completeness and reference healing: re-select any canonical
          reward event that is not yet journalised OR whose journal lines still
          carry an unresolved referral, regardless of ingestion window
          (standard-scale repair proof, 2026-07-17).
        -#}
        {{ incremental_ingestion_filter(
            extra_or_clause=(
                'event_id not in (select event_id from ' ~ this ~ ') '
                ~ 'or event_id in (select event_id from ' ~ this
                ~ ' where referral_id is null)'
            ) if is_incremental() else none
        ) }}
),

entries as (
    select
        event_id,
        reward_id,
        referral_id,
        occurred_at,
        ingested_at,
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
        ingested_at,
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
    ingested_at,
    arrival_date
from entries
