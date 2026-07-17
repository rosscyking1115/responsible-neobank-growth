-- Campaign spend family deliveries with payload fields flattened.
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
    {{ json_value('payload', 'campaign_id') }} as campaign_id,
    cast({{ json_value('payload', 'spend_date') }} as date) as spend_date,
    cast({{ json_value('payload', 'amount_minor') }} as {{ integer_type() }}) as amount_minor,
    {{ json_value('payload', 'currency') }} as currency,
    {{ json_value('payload', 'channel') }} as channel
from {{ ref('lnd_event_deliveries') }}
where event_name = 'campaign-spend-recorded'
