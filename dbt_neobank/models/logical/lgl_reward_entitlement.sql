-- One row per qualified referral: the authoritative entitlement and its
-- current reconciliation position. Entitlement rules live here (dbt), never in
-- a BI layer (the dbt/presentation boundary).
with qualified as (
    select
        referral_id,
        min(occurred_at) as qualified_at,
        min(arrival_date) as qualified_arrival_date,
        min(qualification_rule) as qualification_rule
    from {{ ref('nrm_referral_event') }}
    where event_type = 'referral_qualified'
    group by referral_id
),

reward_positions as (
    select
        referral_id,
        min(case when event_type = 'reward_booked' then reward_id end) as reward_id,
        count(case when event_type = 'reward_booked' then 1 end) as booking_count,
        coalesce(sum(case when event_type = 'reward_booked' then amount_minor end), 0)
            as booked_minor,
        coalesce(sum(case when event_type = 'reward_settled' then amount_minor end), 0)
            as settled_minor,
        coalesce(sum(case when event_type = 'reward_reversed' then amount_minor end), 0)
            as reversed_minor,
        min(case when event_type = 'reward_booked' then arrival_date end)
            as booked_arrival_date
    from {{ ref('nrm_reward_event') }}
    where referral_id is not null
    group by referral_id
),

current_state as (
    select referral_id, state as lifecycle_status
    from {{ ref('nrm_referral_history') }}
    where is_current
)

select
    qualified.referral_id,
    reward_positions.reward_id,
    qualified.qualified_at,
    qualified.qualified_arrival_date,
    qualified.qualification_rule,
    {{ var('reward_amount_minor') }} as entitled_minor,
    coalesce(reward_positions.booking_count, 0) as booking_count,
    coalesce(reward_positions.booked_minor, 0) as booked_minor,
    coalesce(reward_positions.settled_minor, 0) as settled_minor,
    coalesce(reward_positions.reversed_minor, 0) as reversed_minor,
    coalesce(reward_positions.booked_minor, 0)
        - coalesce(reward_positions.settled_minor, 0)
        - coalesce(reward_positions.reversed_minor, 0) as outstanding_payable_minor,
    coalesce(current_state.lifecycle_status, 'qualified') as lifecycle_status,
    case
        when coalesce(reward_positions.booking_count, 0) = 0 then 'missing_posting'
        when reward_positions.booking_count > 1 then 'duplicate_posting'
        when reward_positions.booked_minor != {{ var('reward_amount_minor') }}
            then 'amount_mismatch'
        when reward_positions.settled_minor > 0 and reward_positions.booked_minor = 0
            then 'settlement_without_booking'
        when reward_positions.reversed_minor > reward_positions.booked_minor
            then 'reversal_beyond_booked_amount'
    end as exception_reason
from qualified
left join reward_positions on qualified.referral_id = reward_positions.referral_id
left join current_state on qualified.referral_id = current_state.referral_id
