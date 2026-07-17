-- A reward may settle or reverse, never both.
select reward_id
from {{ ref('nrm_reward_event') }}
where event_type in ('reward_settled', 'reward_reversed')
group by reward_id
having count(distinct event_type) > 1
