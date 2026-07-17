-- The referral interface's Finance figures must equal the authoritative
-- entitlement position (one meaning, one owner — no redefinition downstream).
select economics.referral_id
from {{ ref('lgl_referral_economics') }} as economics
inner join {{ ref('lgl_reward_entitlement') }} as entitlement
    on economics.referral_id = entitlement.referral_id
where economics.booked_minor != entitlement.booked_minor
    or economics.settled_minor != entitlement.settled_minor
    or economics.reversed_minor != entitlement.reversed_minor
    or economics.entitled_minor != entitlement.entitled_minor
