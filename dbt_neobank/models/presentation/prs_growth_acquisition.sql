-- Consumer-shaped Growth acquisition journeys (BI/Streamlit/reporting).
-- Replaceable consumer of lgl_growth_acquisition; never a second source of
-- business truth.
select
    application_id,
    customer_id,
    applied_at,
    cast(applied_at as date) as application_date,
    channel,
    campaign_id,
    referral_id,
    referral_id is not null as is_referred,
    kyc_decision,
    kyc_decided_at,
    account_id,
    activated_at,
    first_funded_at,
    first_funding_amount_minor,
    experiment_id,
    experiment_variant,
    customer_outcome_flag,
    customer_outcome_max_severity,
    journey_stage,
    journey_stage in ('approved', 'activated', 'funded') as is_approved,
    journey_stage in ('activated', 'funded') as is_activated,
    journey_stage = 'funded' as is_funded
from {{ ref('lgl_growth_acquisition') }}
