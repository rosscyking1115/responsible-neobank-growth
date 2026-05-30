select
    exposure_id,
    user_id,
    offer_id,
    cast(exposure_ts as timestamp) as exposure_ts,
    cast(exposure_date as date) as exposure_date,
    price_variant,
    cast(displayed_monthly_fee_gbp as {{ float_type() }}) as displayed_monthly_fee_gbp,
    cast(displayed_incentive_value_gbp as {{ float_type() }}) as displayed_incentive_value_gbp,
    eligibility_reason_code,
    cast(customer_understanding_required as boolean) as customer_understanding_required
from {{ raw_table('pricing_exposures', 'pricing_exposures.parquet') }}
