select
    exposures.exposure_id,
    exposures.user_id,
    exposures.offer_id,
    exposures.exposure_ts,
    exposures.exposure_date,
    exposures.price_variant,
    exposures.displayed_monthly_fee_gbp,
    exposures.displayed_incentive_value_gbp,
    exposures.eligibility_reason_code,
    exposures.customer_understanding_required,
    users.region,
    users.signup_channel,
    users.income_segment,
    users.vulnerable_customer_flag,
    users.business_account_flag,
    offers.product_area,
    offers.offer_type,
    offers.expected_monthly_margin_gbp,
    outcomes.accepted_offer,
    outcomes.activated_offer,
    outcomes.gross_margin_30d_gbp,
    outcomes.incentive_cost_gbp,
    outcomes.net_margin_30d_gbp,
    outcomes.support_contact_14d,
    outcomes.complaint_14d,
    (
        users.vulnerable_customer_flag
        or exposures.customer_understanding_required
        or outcomes.complaint_14d
    ) as human_review_required,
    round(
        offers.expected_monthly_margin_gbp - exposures.displayed_incentive_value_gbp,
        2
    ) as expected_net_margin_before_acceptance_gbp
from {{ ref('stg_pricing_exposures') }} as exposures
inner join {{ ref('stg_pricing_offer_catalog') }} as offers
    on exposures.offer_id = offers.offer_id
inner join {{ ref('stg_users') }} as users
    on exposures.user_id = users.user_id
left join {{ ref('stg_pricing_outcomes') }} as outcomes
    on exposures.exposure_id = outcomes.exposure_id
