select
    offer_id,
    exposure_date,
    region,
    price_variant,
    count(*) as exposures,
    sum(case when accepted_offer then 1 else 0 end) as accepted_offers,
    sum(case when activated_offer then 1 else 0 end) as activated_offers,
    round(avg(case when accepted_offer then 1.0 else 0.0 end), 4) as acceptance_rate,
    round(sum(gross_margin_30d_gbp), 2) as gross_margin_30d_gbp,
    round(sum(incentive_cost_gbp), 2) as incentive_cost_gbp,
    round(sum(net_margin_30d_gbp), 2) as net_margin_30d_gbp,
    round(avg(case when support_contact_14d then 1.0 else 0.0 end), 4) as support_contact_rate_14d,
    round(avg(case when complaint_14d then 1.0 else 0.0 end), 4) as complaint_rate_14d,
    sum(case when human_review_required then 1 else 0 end) as human_review_required_exposures
from {{ ref('fct_offer_exposures') }}
group by 1, 2, 3, 4
