select
    offer_id,
    product_area,
    offer_type,
    income_segment,
    price_variant,
    count(*) as exposures,
    round(avg(case when accepted_offer then 1.0 else 0.0 end), 4) as acceptance_rate,
    round(avg(net_margin_30d_gbp), 2) as avg_net_margin_30d_gbp,
    round(sum(net_margin_30d_gbp), 2) as total_net_margin_30d_gbp,
    round(avg(case when support_contact_14d then 1.0 else 0.0 end), 4) as support_contact_rate_14d,
    round(avg(case when complaint_14d then 1.0 else 0.0 end), 4) as complaint_rate_14d,
    round(avg(case when human_review_required then 1.0 else 0.0 end), 4) as human_review_rate,
    case
        when avg(case when human_review_required then 1.0 else 0.0 end) >= 0.20
            then 'human_review'
        when avg(net_margin_30d_gbp) < 0
            then 'hold_margin'
        when avg(case when complaint_14d then 1.0 else 0.0 end) > 0.025
            then 'hold_guardrail'
        when avg(case when accepted_offer then 1.0 else 0.0 end) >= 0.18
            and avg(net_margin_30d_gbp) >= 0.20
            then 'scale'
        else 'test'
    end as recommended_action,
    case
        when avg(case when human_review_required then 1.0 else 0.0 end) >= 0.20
            then 'customer_understanding_review'
        when avg(net_margin_30d_gbp) < 0
            then 'negative_unit_economics'
        when avg(case when complaint_14d then 1.0 else 0.0 end) > 0.025
            then 'complaint_guardrail'
        when avg(case when accepted_offer then 1.0 else 0.0 end) >= 0.18
            and avg(net_margin_30d_gbp) >= 0.20
            then 'positive_margin_and_conversion'
        else 'insufficient_signal'
    end as recommendation_reason_code
from {{ ref('fct_offer_exposures') }}
group by 1, 2, 3, 4, 5
