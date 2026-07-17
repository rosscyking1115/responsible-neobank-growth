-- Quarantine is evidence, not silent dropping: every invalid delivery with its
-- failing rule, severity and raw payload hash. No canonical state derives from
-- this model.
select
    event_id,
    event_name,
    source_service,
    cast(ingested_at as timestamp) as ingested_at,
    cast(schema_version as {{ integer_type() }}) as schema_version,
    payload_raw,
    payload_hash,
    error_code,
    error_message,
    cast(retriable as boolean) as retriable,
    severity,
    scenario_id,
    batch_id,
    run_id,
    cast(arrival_date as date) as arrival_date
from {{ event_quarantine_table() }}
