select
    user_id,
    variant,
    cast(activated_d7_ground_truth as boolean) as activated_d7_ground_truth,
    cast(activated_ever_ground_truth as boolean) as activated_ever_ground_truth,
    cast(first_transaction_ts_ground_truth as timestamp) as first_transaction_ts_ground_truth,
    cast(d7_activation_probability as {{ float_type() }}) as d7_activation_probability
from {{ raw_table('activation_ground_truth', 'activation_ground_truth.parquet') }}
