-- Governed interface: growth_acquisition (contracts/interfaces/growth-acquisition.yml).
-- One row per customer application journey: application -> KYC -> activation ->
-- first funding, with experiment arm and synthetic customer-outcome guardrail.
-- Growth owns meaning; platform owns reliability.
with applications as (
    select
        application_id,
        customer_id,
        channel,
        campaign_id,
        referral_id,
        occurred_at as applied_at
    from {{ ref('nrm_application_event') }}
    where event_type = 'application_submitted'
),

kyc as (
    select
        application_id,
        decision as kyc_decision,
        decision_source as kyc_decision_source,
        occurred_at as kyc_decided_at
    from {{ ref('nrm_application_event') }}
    where event_type = 'kyc_decisioned'
),

activations as (
    select
        application_id,
        account_id,
        occurred_at as activated_at
    from {{ ref('nrm_account_event') }}
    where event_type = 'account_activated'
),

funding as (
    select
        account_id,
        first_funded_at,
        first_funding_amount_minor
    from {{ ref('nrm_account_current') }}
),

experiment as (
    select
        customer_id,
        min(experiment_id) as experiment_id,
        min(variant) as experiment_variant
    from {{ ref('nrm_experiment_assignment') }}
    group by customer_id
),

outcomes as (
    select
        customer_id,
        count(*) as outcome_event_count,
        max(case severity when 'high' then 3 when 'medium' then 2 else 1 end)
            as outcome_severity_rank
    from {{ ref('nrm_customer_outcome_event') }}
    group by customer_id
)

select
    applications.application_id,
    applications.customer_id,
    applications.applied_at,
    applications.channel,
    applications.campaign_id,
    applications.referral_id,
    kyc.kyc_decision,
    kyc.kyc_decision_source,
    kyc.kyc_decided_at,
    activations.account_id,
    activations.activated_at,
    funding.first_funded_at,
    funding.first_funding_amount_minor,
    experiment.experiment_id,
    experiment.experiment_variant,
    coalesce(outcomes.outcome_event_count, 0) > 0 as customer_outcome_flag,
    case outcomes.outcome_severity_rank
        when 3 then 'high' when 2 then 'medium' when 1 then 'low'
    end as customer_outcome_max_severity,
    case
        when funding.first_funded_at is not null then 'funded'
        when activations.activated_at is not null then 'activated'
        when kyc.kyc_decision = 'approved' then 'approved'
        when kyc.kyc_decision in ('rejected', 'manual_review') then kyc.kyc_decision
        else 'applied'
    end as journey_stage
from applications
left join kyc on applications.application_id = kyc.application_id
left join activations on applications.application_id = activations.application_id
left join funding on activations.account_id = funding.account_id
left join experiment on applications.customer_id = experiment.customer_id
left join outcomes on applications.customer_id = outcomes.customer_id
