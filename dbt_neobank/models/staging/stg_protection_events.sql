select
    protection_event_id,
    user_id,
    cast(event_date as date) as event_date,
    cast(amount_gbp as {{ float_type() }}) as amount_gbp,
    cast(new_payee as boolean) as new_payee,
    cast(first_large_transfer as boolean) as first_large_transfer,
    cast(unusual_time as boolean) as unusual_time,
    cast(recent_device_change as boolean) as recent_device_change,
    cast(viewed_scam_warning as boolean) as viewed_scam_warning,
    cast(ignored_warning as boolean) as ignored_warning,
    cast(confirmed_transfer as boolean) as confirmed_transfer,
    cast(support_contact_about_scam as boolean) as support_contact_about_scam,
    cast(investment_context as boolean) as investment_context,
    cast(vulnerable_customer as boolean) as vulnerable_customer
from {{ raw_table('protection_events', 'protection_events.parquet') }}
