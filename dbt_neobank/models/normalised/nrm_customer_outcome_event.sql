-- Canonical customer-outcome guardrail events. Synthetic proxies only; never
-- inputs to punitive decisions (docs/FINANCIAL_WELLBEING_PROXIES.md).
select
    idempotency_key as canonical_event_key,
    event_id,
    customer_id,
    outcome_type,
    severity,
    occurred_at,
    ingested_at,
    arrival_date
from {{ ref('lnd_customer_outcome_events') }}
where is_canonical
