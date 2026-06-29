with wb as (
    select
        user_id,
        income_band,
        digital_confidence_score,
        accessibility_need_proxy,
        new_to_uk_proxy,
        vulnerable_customer_proxy
    from {{ ref('stg_wellbeing_proxies') }}
)

select
    ob.user_id,
    users.region,
    users.income_segment,
    wb.income_band,
    case
        when wb.digital_confidence_score < 0.40 then 'low'
        when wb.digital_confidence_score < 0.70 then 'medium'
        else 'high'
    end as digital_confidence_band,
    wb.accessibility_need_proxy,
    wb.new_to_uk_proxy,
    wb.vulnerable_customer_proxy,
    ob.identity_check_started,
    ob.identity_check_passed,
    ob.card_activated,
    ob.completed_onboarding,
    ob.furthest_step,
    ob.abandoned_step,
    ob.needs_assisted_onboarding
from {{ ref('stg_onboarding_events') }} as ob
left join {{ ref('stg_users') }} as users
    on ob.user_id = users.user_id
left join wb
    on ob.user_id = wb.user_id
