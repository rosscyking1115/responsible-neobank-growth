with support as (
    select
        user_id,
        count(*) as support_contacts,
        sum(case when is_complaint then 1 else 0 end) as complaints
    from {{ ref('stg_support_contacts') }}
    group by 1
),

feature_adoption as (
    select
        user_id,
        max(case when feature_name = 'savings_pot' then 1 else 0 end) as adopted_savings_pot,
        max(case when feature_name = 'salary_sorter' then 1 else 0 end) as adopted_salary_sorter
    from {{ ref('stg_feature_events') }}
    group by 1
),

sessions as (
    select
        user_id,
        sum(case when app_crashed then 1 else 0 end) as app_crashes
    from {{ ref('stg_sessions') }}
    group by 1
)

select
    assignments.experiment_name,
    assignments.user_id,
    assignments.variant,
    assignments.assignment_bucket,
    activation.signup_date,
    activation.region,
    activation.signup_channel,
    activation.income_segment,
    activation.vulnerable_customer_flag,
    activation.activated_d7,
    activation.activated_ever,
    coalesce(feature_adoption.adopted_savings_pot, 0)::boolean as adopted_savings_pot,
    coalesce(feature_adoption.adopted_salary_sorter, 0)::boolean as adopted_salary_sorter,
    coalesce(support.support_contacts, 0) as support_contacts,
    coalesce(support.complaints, 0) as complaints,
    coalesce(sessions.app_crashes, 0) as app_crashes
from {{ ref('stg_experiment_assignments') }} as assignments
inner join {{ ref('fct_activation') }} as activation
    on assignments.user_id = activation.user_id
left join support
    on assignments.user_id = support.user_id
left join feature_adoption
    on assignments.user_id = feature_adoption.user_id
left join sessions
    on assignments.user_id = sessions.user_id
