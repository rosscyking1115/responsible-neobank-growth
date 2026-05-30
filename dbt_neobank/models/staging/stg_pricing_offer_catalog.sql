select
    offer_id,
    offer_name,
    product_area,
    offer_type,
    cast(monthly_fee_gbp as {{ float_type() }}) as monthly_fee_gbp,
    cast(base_incentive_cost_gbp as {{ float_type() }}) as base_incentive_cost_gbp,
    cast(expected_monthly_margin_gbp as {{ float_type() }}) as expected_monthly_margin_gbp,
    cast(vulnerable_customer_eligible as boolean) as vulnerable_customer_eligible
from {{ raw_table('pricing_offer_catalog', 'pricing_offer_catalog.parquet') }}
