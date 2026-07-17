-- Funnel invariants: activation implies KYC approval; funding implies
-- activation; a rejected application never activates.
select application_id
from {{ ref('lgl_growth_acquisition') }}
where (activated_at is not null and kyc_decision != 'approved')
    or (first_funded_at is not null and activated_at is null)
    or (first_funded_at is not null and first_funded_at < activated_at)
