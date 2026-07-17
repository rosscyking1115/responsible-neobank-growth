-- Referral family deliveries (invited/qualified, v1 and v2) with payload
-- fields flattened. Version adaptation to canonical meaning happens in
-- nrm_referral_event, not here.
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
    {{ json_value('payload', 'referral_id') }} as referral_id,
    {{ json_value('payload', 'referrer_customer_id') }} as referrer_customer_id,
    {{ json_value('payload', 'referred_customer_id') }} as referred_customer_id,
    {{ json_value('payload', 'invite_channel') }} as invite_channel,
    {{ json_value('payload', 'qualified_reason') }} as qualified_reason,
    {{ json_value('payload', 'qualification_rule') }} as qualification_rule,
    {{ json_value('payload', 'qualifying_account_id') }} as qualifying_account_id
from {{ ref('lnd_event_deliveries') }}
where event_name in ('referral-invited', 'referral-qualified')
