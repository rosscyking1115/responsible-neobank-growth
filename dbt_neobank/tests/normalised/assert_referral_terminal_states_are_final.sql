-- Nothing may follow a terminal referral state (settled or reversed).
select referral_id, state, valid_to
from {{ ref('nrm_referral_history') }}
where state in ('settled', 'reversed') and valid_to is not null
