-- Compatibility view: customer-outcome guardrail counts per customer served
-- from the governed interface (Customer outcomes tab / release-gate engine
-- signal grain). Wellbeing proxy attributes remain on the preserved batch
-- models (stg_wellbeing_proxies) with their RBAC boundaries.
select
    customer_id as user_id,
    count(*) as outcome_events,
    sum(case when outcome_type = 'complaint' then 1 else 0 end) as complaint_count,
    sum(case when outcome_type = 'support_contact' then 1 else 0 end) as support_contact_count,
    sum(case when outcome_type = 'hardship_indicator' then 1 else 0 end) as hardship_count,
    max(case severity when 'high' then 3 when 'medium' then 2 else 1 end) as max_severity_rank
from {{ ref('nrm_customer_outcome_event') }}
group by customer_id
