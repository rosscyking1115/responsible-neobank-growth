-- Every journal (per reward event) must balance: debit equals credit.
select event_id
from {{ ref('nrm_reward_ledger_entry') }}
group by event_id
having sum(case when entry_side = 'debit' then amount_minor else 0 end)
    != sum(case when entry_side = 'credit' then amount_minor else 0 end)
