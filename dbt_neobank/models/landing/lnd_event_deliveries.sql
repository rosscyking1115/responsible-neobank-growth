-- Typed envelope over the raw delivery store. Owns delivery-versus-canonical
-- identity: is_canonical marks the first delivery per idempotency key by
-- arrival, so downstream canonical models deduplicate exactly once here.
select
    event_id,
    idempotency_key,
    event_name,
    source_service,
    cast(occurred_at as timestamp) as occurred_at,
    cast(emitted_at as timestamp) as emitted_at,
    cast(ingested_at as timestamp) as ingested_at,
    cast(schema_version as {{ integer_type() }}) as schema_version,
    producer_id,
    trace_id,
    payload,
    payload_hash,
    generator_version,
    scenario_id,
    batch_id,
    run_id,
    cast(arrival_date as date) as arrival_date,
    row_number() over (
        partition by idempotency_key
        order by ingested_at, event_id
    ) as delivery_number,
    row_number() over (
        partition by idempotency_key
        order by ingested_at, event_id
    ) = 1 as is_canonical
from {{ event_deliveries_table() }}
