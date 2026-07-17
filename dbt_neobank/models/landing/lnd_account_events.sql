-- Activation/funding family deliveries with payload fields flattened.
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
    {{ json_value('payload', 'account_id') }} as account_id,
    {{ json_value('payload', 'customer_id') }} as customer_id,
    {{ json_value('payload', 'application_id') }} as application_id,
    cast({{ json_value('payload', 'amount_minor') }} as {{ integer_type() }}) as amount_minor,
    {{ json_value('payload', 'currency') }} as currency,
    {{ json_value('payload', 'funding_method') }} as funding_method,
    cast({{ json_value('payload', 'is_first_funding') }} as boolean) as is_first_funding
from {{ ref('lnd_event_deliveries') }}
where event_name in ('account-activated', 'account-funded')
