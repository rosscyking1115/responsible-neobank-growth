select
    support_contact_id,
    user_id,
    cast(contact_ts as timestamp) as contact_ts,
    cast(contact_date as date) as contact_date,
    region,
    topic,
    cast(is_complaint as boolean) as is_complaint,
    cast(resolved_first_contact as boolean) as resolved_first_contact
from {{ raw_table('support_contacts', 'support_contacts.parquet') }}
