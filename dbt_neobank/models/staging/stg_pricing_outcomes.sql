select
    exposure_id,
    user_id,
    offer_id,
    cast(accepted_offer as boolean) as accepted_offer,
    cast(activated_offer as boolean) as activated_offer,
    cast(outcome_ts as timestamp) as outcome_ts,
    cast(gross_margin_30d_gbp as {{ float_type() }}) as gross_margin_30d_gbp,
    cast(incentive_cost_gbp as {{ float_type() }}) as incentive_cost_gbp,
    cast(net_margin_30d_gbp as {{ float_type() }}) as net_margin_30d_gbp,
    cast(support_contact_14d as boolean) as support_contact_14d,
    cast(complaint_14d as boolean) as complaint_14d
from {{ raw_table('pricing_outcomes', 'pricing_outcomes.parquet') }}
