select
    user_id
from {{ ref('fct_user_clv_proxy') }}
where lifetime_interchange_revenue_gbp < 0
    or support_cost_gbp < 0
    or complaint_cost_gbp < 0
