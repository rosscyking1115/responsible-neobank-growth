-- Governed interface: referral_economics (contracts/interfaces/referral-economics.yml).
-- One row per referral: qualification, activation outcome and Finance-owned
-- booked reward cost. Incrementality estimate columns are declared but null in
-- Plan 2 — they are populated only from governed experiment outputs, never
-- recomputed in a BI layer (docs/metrics/metric-ownership.yml).
with invitations as (
    select
        referral_id,
        referrer_customer_id,
        invite_channel,
        occurred_at as invited_at
    from {{ ref('nrm_referral_event') }}
    where event_type = 'referral_invited'
),

qualifications as (
    select
        referral_id,
        referred_customer_id,
        qualified_reason,
        qualification_rule,
        occurred_at as qualified_at
    from {{ ref('nrm_referral_event') }}
    where event_type = 'referral_qualified'
),

rewards as (
    select
        referral_id,
        reward_id,
        entitled_minor,
        booked_minor,
        settled_minor,
        reversed_minor,
        outstanding_payable_minor,
        lifecycle_status,
        exception_reason
    from {{ ref('lgl_reward_entitlement') }}
),

referred_activation as (
    select
        referral_id,
        max(case when journey_stage = 'funded' then 1 else 0 end) = 1
            as referred_customer_funded
    from {{ ref('lgl_growth_acquisition') }}
    where referral_id is not null
    group by referral_id
)

select
    invitations.referral_id,
    invitations.referrer_customer_id,
    invitations.invite_channel,
    invitations.invited_at,
    {{ date_trunc_day('month', 'invitations.invited_at') }} as invite_cohort_month,
    qualifications.referred_customer_id,
    qualifications.qualified_at,
    qualifications.qualified_reason,
    qualifications.qualification_rule,
    qualifications.qualified_at is not null as is_qualified,
    coalesce(referred_activation.referred_customer_funded, false)
        as referred_customer_funded,
    rewards.reward_id,
    coalesce(rewards.entitled_minor, 0) as entitled_minor,
    coalesce(rewards.booked_minor, 0) as booked_minor,
    coalesce(rewards.settled_minor, 0) as settled_minor,
    coalesce(rewards.reversed_minor, 0) as reversed_minor,
    coalesce(rewards.outstanding_payable_minor, 0) as outstanding_payable_minor,
    coalesce(rewards.lifecycle_status, 'invited') as lifecycle_status,
    rewards.exception_reason,
    -- Populated only from governed experiment outputs (Plan 2: not computed).
    cast(null as {{ float_type() }}) as incremental_activated_estimate,
    cast(null as {{ float_type() }}) as incremental_activated_ci_low,
    cast(null as {{ float_type() }}) as incremental_activated_ci_high,
    cast(null as varchar) as estimate_method
from invitations
left join qualifications on invitations.referral_id = qualifications.referral_id
left join rewards on invitations.referral_id = rewards.referral_id
left join referred_activation on invitations.referral_id = referred_activation.referral_id
