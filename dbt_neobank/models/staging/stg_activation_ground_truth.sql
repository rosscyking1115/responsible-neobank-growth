select
    user_id,
    variant,
    cast(activated_d7_ground_truth as boolean) as activated_d7_ground_truth,
    cast(activated_ever_ground_truth as boolean) as activated_ever_ground_truth,
    cast(first_transaction_ts_ground_truth as timestamp) as first_transaction_ts_ground_truth,
    cast(d7_activation_probability as double) as d7_activation_probability
from read_parquet('{{ var("raw_path", "raw/ci") }}/activation_ground_truth.parquet')
