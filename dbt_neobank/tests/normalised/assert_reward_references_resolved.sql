-- A canonical settlement/reversal may not keep a null referral once its
-- booking is present in landing (out-of-order arrival must self-heal on the
-- next incremental run; found by the standard-scale repair proof).
select events.reward_id
from {{ ref('nrm_reward_event') }} as events
where events.referral_id is null
    and events.reward_id in (
        select reward_id
        from {{ ref('lnd_reward_events') }}
        where event_name = 'reward-booked' and is_canonical
    )
