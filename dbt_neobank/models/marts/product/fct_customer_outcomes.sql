with support as (
    select
        user_id,
        count(*) as support_contact_count,
        max(case when is_complaint then 1 else 0 end) as complaint_flag
    from {{ ref('stg_support_contacts') }}
    group by 1
),

base as (
    select
        activation.user_id,
        activation.region,
        activation.income_segment,
        activation.vulnerable_customer_flag,
        activation.activated_d7,
        wb.income_band,
        wb.digital_confidence_score,
        wb.vulnerable_customer_proxy,
        wb.accessibility_need_proxy,
        wb.new_to_uk_proxy,
        wb.student_proxy,
        coalesce(support.support_contact_count, 0) as support_contact_count,
        coalesce(support.complaint_flag, 0) as complaint_flag
    from {{ ref('fct_activation') }} as activation
    left join {{ ref('stg_wellbeing_proxies') }} as wb
        on activation.user_id = wb.user_id
    left join support
        on activation.user_id = support.user_id
)

select
    user_id,
    region,
    income_segment,
    income_band,
    case
        when digital_confidence_score < 0.40 then 'low'
        when digital_confidence_score < 0.70 then 'medium'
        else 'high'
    end as digital_confidence_band,
    vulnerable_customer_proxy,
    accessibility_need_proxy,
    new_to_uk_proxy,
    student_proxy,
    activated_d7,
    support_contact_count,
    support_contact_count > 0 as has_support_contact,
    cast(complaint_flag as boolean) as has_complaint
from base
