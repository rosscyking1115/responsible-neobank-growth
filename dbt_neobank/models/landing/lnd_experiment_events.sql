-- Experiment assignment family deliveries with payload fields flattened.
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
    {{ json_value('payload', 'experiment_id') }} as experiment_id,
    {{ json_value('payload', 'customer_id') }} as customer_id,
    {{ json_value('payload', 'variant') }} as variant,
    {{ json_value('payload', 'assignment_unit') }} as assignment_unit
from {{ ref('lnd_event_deliveries') }}
where event_name = 'experiment-assigned'
