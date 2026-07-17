-- Application/KYC family deliveries with payload fields flattened. No
-- business metrics: extraction and typing only.
select
    event_id,
    idempotency_key,
    event_name,
    occurred_at,
    emitted_at,
    ingested_at,
    schema_version,
    trace_id,
    arrival_date,
    is_canonical,
    {{ json_value('payload', 'application_id') }} as application_id,
    {{ json_value('payload', 'customer_id') }} as customer_id,
    {{ json_value('payload', 'channel') }} as channel,
    {{ json_value('payload', 'campaign_id') }} as campaign_id,
    {{ json_value('payload', 'referral_id') }} as referral_id,
    {{ json_value('payload', 'requested_product') }} as requested_product,
    {{ json_value('payload', 'decision') }} as decision,
    {{ json_value('payload', 'decision_source') }} as decision_source
from {{ ref('lnd_event_deliveries') }}
where event_name in ('application-submitted', 'kyc-decisioned')
