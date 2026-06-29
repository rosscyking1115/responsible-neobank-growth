select
    customer_id as user_id,
    income_band,
    cast(income_volatility_score as {{ float_type() }}) as income_volatility_score,
    cast(salary_regularity_score as {{ float_type() }}) as salary_regularity_score,
    cast(cash_buffer_proxy as {{ float_type() }}) as cash_buffer_proxy,
    cast(bill_pressure_score as {{ float_type() }}) as bill_pressure_score,
    cast(overdraft_risk_proxy as {{ float_type() }}) as overdraft_risk_proxy,
    cast(missed_payment_proxy as boolean) as missed_payment_proxy,
    cast(support_contact_frequency as {{ integer_type() }}) as support_contact_frequency,
    cast(complaint_history_flag as boolean) as complaint_history_flag,
    cast(digital_confidence_score as {{ float_type() }}) as digital_confidence_score,
    cast(accessibility_need_proxy as boolean) as accessibility_need_proxy,
    cast(new_to_uk_proxy as boolean) as new_to_uk_proxy,
    cast(student_proxy as boolean) as student_proxy,
    cast(vulnerable_customer_proxy as boolean) as vulnerable_customer_proxy
from {{ raw_table('wellbeing_proxies', 'wellbeing_proxies.parquet') }}
