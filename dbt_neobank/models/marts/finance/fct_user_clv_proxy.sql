with support_cost as (
    select
        user_id,
        count(*) * 3.50 as support_cost_gbp,
        sum(case when is_complaint then 1 else 0 end) * 8.00 as complaint_cost_gbp
    from {{ ref('stg_support_contacts') }}
    group by 1
),

features as (
    select
        user_id,
        max(case when feature_name = 'easy_access_savings' then 1 else 0 end) as has_savings,
        max(case when feature_name = 'salary_sorter' then 1 else 0 end) as has_salary_sorter
    from {{ ref('stg_feature_events') }}
    group by 1
)

select
    activation.user_id,
    activation.region,
    activation.signup_channel,
    activation.income_segment,
    activation.activated_d7,
    activation.lifetime_interchange_revenue_gbp,
    case
        when coalesce(features.has_savings, 0) = 1 then 12.00
        else 0.00
    end as savings_margin_proxy_gbp,
    case
        when coalesce(features.has_salary_sorter, 0) = 1 then 18.00
        else 0.00
    end as primary_banking_margin_proxy_gbp,
    coalesce(support_cost.support_cost_gbp, 0) as support_cost_gbp,
    coalesce(support_cost.complaint_cost_gbp, 0) as complaint_cost_gbp,
    activation.lifetime_interchange_revenue_gbp
        + case when coalesce(features.has_savings, 0) = 1 then 12.00 else 0.00 end
        + case when coalesce(features.has_salary_sorter, 0) = 1 then 18.00 else 0.00 end
        - coalesce(support_cost.support_cost_gbp, 0)
        - coalesce(support_cost.complaint_cost_gbp, 0) as clv_proxy_12m_gbp
from {{ ref('fct_activation') }} as activation
left join support_cost
    on activation.user_id = support_cost.user_id
left join features
    on activation.user_id = features.user_id
