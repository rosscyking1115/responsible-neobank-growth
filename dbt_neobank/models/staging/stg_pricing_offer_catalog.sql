select
    offer_id,
    offer_name,
    product_area,
    offer_type,
    cast(monthly_fee_gbp as double) as monthly_fee_gbp,
    cast(base_incentive_cost_gbp as double) as base_incentive_cost_gbp,
    cast(expected_monthly_margin_gbp as double) as expected_monthly_margin_gbp,
    cast(vulnerable_customer_eligible as boolean) as vulnerable_customer_eligible
from read_parquet('{{ var("raw_path", "raw/ci") }}/pricing_offer_catalog.parquet')
