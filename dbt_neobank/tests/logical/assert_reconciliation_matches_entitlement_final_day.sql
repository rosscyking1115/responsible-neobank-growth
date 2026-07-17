-- Opening plus movements equals closing: the latest reconciliation day must
-- agree with the authoritative entitlement position for every referral.
with final_day as (
    select *
    from {{ ref('lgl_reward_ledger_reconciliation') }}
    where reconciliation_date = (
        select max(reconciliation_date) from {{ ref('lgl_reward_ledger_reconciliation') }}
    )
)

select entitlement.referral_id
from {{ ref('lgl_reward_entitlement') }} as entitlement
inner join final_day on entitlement.referral_id = final_day.referral_id
where entitlement.booked_minor != final_day.booked_minor
    or entitlement.settled_minor != final_day.settled_minor
    or entitlement.reversed_minor != final_day.reversed_minor
    or entitlement.outstanding_payable_minor != final_day.outstanding_payable_minor
