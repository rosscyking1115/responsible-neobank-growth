-- Canonical referral lifecycle events with v1/v2 payload adaptation: v1 and
-- v2 qualifications share one canonical meaning; v1 rows expose a null
-- qualification_rule (documented new nullable field, ADR-route-c-event-boundary).
select
    idempotency_key as canonical_event_key,
    event_id,
    replace(event_name, '-', '_') as event_type,
    referral_id,
    referrer_customer_id,
    referred_customer_id,
    invite_channel,
    qualified_reason,
    qualification_rule,
    qualifying_account_id,
    schema_version,
    occurred_at,
    ingested_at,
    arrival_date
from {{ ref('lnd_referral_events') }}
where is_canonical
