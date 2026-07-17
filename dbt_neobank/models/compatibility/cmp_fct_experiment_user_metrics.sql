-- Compatibility view: the anchor consumer contract (Gate G0.4). Serves the
-- Experiments tab / release-gate engine metric grain entirely from governed
-- interfaces: assignment, activation outcome and customer-outcome guardrail.
-- Batch-universe covariates (income segment, device, propensities) are not
-- served by the event boundary; declared in compatibility.yml.
with assignments as (
    select experiment_id, customer_id, variant
    from {{ ref('nrm_experiment_assignment') }}
),

activation as (
    select
        user_id,
        signup_date,
        signup_channel,
        activated_d7,
        activated_ever
    from {{ ref('cmp_fct_activation') }}
),

outcomes as (
    select
        customer_id,
        count(*) as support_contacts,
        sum(case when outcome_type = 'complaint' then 1 else 0 end) as complaints
    from {{ ref('nrm_customer_outcome_event') }}
    group by customer_id
)

select
    assignments.experiment_id as experiment_name,
    assignments.customer_id as user_id,
    assignments.variant,
    activation.signup_date,
    activation.signup_channel,
    activation.activated_d7,
    activation.activated_ever,
    coalesce(outcomes.support_contacts, 0) as support_contacts,
    coalesce(outcomes.complaints, 0) as complaints
from assignments
inner join activation on assignments.customer_id = activation.user_id
left join outcomes on assignments.customer_id = outcomes.customer_id
