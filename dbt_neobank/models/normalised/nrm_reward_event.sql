{{ config(
    materialized='incremental',
    unique_key='canonical_event_key',
    incremental_strategy=('merge' if target.type == 'bigquery' else 'delete+insert'),
    partition_by={'field': 'arrival_date', 'data_type': 'date', 'granularity': 'day'},
    cluster_by=['event_type'],
    labels={'project': 'neobank', 'layer': 'normalised'}
) }}

-- Canonical reward lifecycle events (booked/settled/reversed). Settlements
-- and reversals carry no referral_id in their payloads, so it is resolved
-- through the booking's reward -> referral mapping (the mapping always reads
-- the full canonical landing set, so late settlements resolve against
-- earlier bookings).
with reward_events as (
    select *
    from {{ ref('lnd_reward_events') }}
    where is_canonical
        {#-
          Out-of-order arrival repair: a settlement/reversal that arrived
          before its booking resolves referral_id to null; such rows are
          re-selected on every incremental run until the booking mapping
          resolves them (found by the standard-scale repair proof, 2026-07-17).
        -#}
        {{ incremental_ingestion_filter(
            extra_or_clause=(
                'idempotency_key in (select canonical_event_key from '
                ~ this ~ ' where referral_id is null)'
            ) if is_incremental() else none
        ) }}
),

all_bookings as (
    select *
    from {{ ref('lnd_reward_events') }}
    where is_canonical
),

reward_to_referral as (
    select reward_id, min(referral_id) as referral_id
    from all_bookings
    where event_name = 'reward-booked'
    group by reward_id
)

select
    reward_events.idempotency_key as canonical_event_key,
    reward_events.event_id,
    replace(reward_events.event_name, '-', '_') as event_type,
    reward_events.reward_id,
    coalesce(reward_events.referral_id, reward_to_referral.referral_id) as referral_id,
    reward_events.beneficiary_customer_id,
    reward_events.settlement_id,
    reward_events.reversal_id,
    reward_events.amount_minor,
    reward_events.currency,
    reward_events.reversal_reason,
    reward_events.occurred_at,
    reward_events.ingested_at,
    reward_events.arrival_date
from reward_events
left join reward_to_referral on reward_events.reward_id = reward_to_referral.reward_id
