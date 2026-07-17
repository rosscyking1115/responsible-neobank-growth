-- Canonical campaign spend records, integer minor units.
select
    idempotency_key as canonical_event_key,
    event_id,
    campaign_id,
    spend_date,
    amount_minor,
    currency,
    channel,
    occurred_at,
    ingested_at,
    arrival_date
from {{ ref('lnd_campaign_events') }}
where is_canonical
