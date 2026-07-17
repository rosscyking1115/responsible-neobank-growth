-- Feature view for the activation-model consumers (batch scoring/API): one row
-- per customer application journey, served from the governed interface so ML
-- never reads version-specific landing payloads.
select
    application_id,
    customer_id,
    cast(applied_at as date) as application_date,
    channel,
    is_referred,
    experiment_variant,
    is_approved,
    is_activated,
    is_funded,
    first_funding_amount_minor,
    customer_outcome_flag
from {{ ref('prs_growth_acquisition') }}
