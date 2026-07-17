-- Canonical account lifecycle events (activated, funded) with integer
-- minor-unit currency.
select
    idempotency_key as canonical_event_key,
    event_id,
    replace(event_name, '-', '_') as event_type,
    account_id,
    customer_id,
    application_id,
    amount_minor,
    currency,
    funding_method,
    is_first_funding,
    occurred_at,
    ingested_at,
    arrival_date
from {{ ref('lnd_account_events') }}
where is_canonical
