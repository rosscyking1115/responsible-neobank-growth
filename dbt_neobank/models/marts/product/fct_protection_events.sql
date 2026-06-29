-- Transfer-level scam-intervention risk events. The supportive intervention decision
-- is applied by the Python rules engine (src/protection) rather than duplicated in
-- SQL, so this mart is the cleaned event feed those rules consume.
select
    protection_event_id,
    user_id,
    event_date,
    amount_gbp,
    new_payee,
    first_large_transfer,
    unusual_time,
    recent_device_change,
    viewed_scam_warning,
    ignored_warning,
    confirmed_transfer,
    support_contact_about_scam,
    investment_context,
    vulnerable_customer
from {{ ref('stg_protection_events') }}
