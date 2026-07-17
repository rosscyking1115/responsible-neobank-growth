-- Referral state intervals reconstructed from canonical referral and reward
-- events, ordered by business occurrence time with deterministic tie-breakers.
-- States follow the locked lifecycle: invited -> qualified -> booked ->
-- settled | reversed.
with referral_states as (
    select
        referral_id,
        case event_type
            when 'referral_invited' then 'invited'
            when 'referral_qualified' then 'qualified'
        end as state,
        occurred_at,
        event_id
    from {{ ref('nrm_referral_event') }}

    union all

    select
        referral_id,
        case event_type
            when 'reward_booked' then 'booked'
            when 'reward_settled' then 'settled'
            when 'reward_reversed' then 'reversed'
        end as state,
        occurred_at,
        event_id
    from {{ ref('nrm_reward_event') }}
    where referral_id is not null
)

select
    referral_id,
    state,
    occurred_at as valid_from,
    lead(occurred_at) over (
        partition by referral_id order by occurred_at, event_id
    ) as valid_to,
    lead(occurred_at) over (
        partition by referral_id order by occurred_at, event_id
    ) is null as is_current
from referral_states
