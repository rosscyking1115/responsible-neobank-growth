select
    user_id,
    cast(signup_ts as timestamp) as signup_ts,
    cast(signup_date as date) as signup_date,
    signup_month,
    region,
    signup_channel,
    device_os,
    cast(age as integer) as age,
    income_segment,
    cast(push_opt_in as boolean) as push_opt_in,
    cast(vulnerable_customer_flag as boolean) as vulnerable_customer_flag,
    cast(business_account_flag as boolean) as business_account_flag,
    cast(d7_activation_probability_control as double) as d7_activation_probability_control,
    cast(primary_bank_propensity as double) as primary_bank_propensity
from read_parquet('{{ var("raw_path", "raw/ci") }}/users.parquet')
