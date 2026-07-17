-- Customer-outcome guardrail deliveries with payload fields flattened.
-- Synthetic proxies only; use boundaries per docs/FINANCIAL_WELLBEING_PROXIES.md.
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
    {{ json_value('payload', 'customer_id') }} as customer_id,
    {{ json_value('payload', 'outcome_type') }} as outcome_type,
    {{ json_value('payload', 'severity') }} as severity
from {{ ref('lnd_event_deliveries') }}
where event_name = 'customer-outcome-recorded'
