-- Every canonical reward event must be journalised with exactly two ledger
-- lines (completeness under out-of-order arrival; standard-scale repair proof).
select events.event_id
from {{ ref('nrm_reward_event') }} as events
left join {{ ref('nrm_reward_ledger_entry') }} as entries
    on events.event_id = entries.event_id
group by events.event_id
having count(entries.ledger_entry_id) != 2
