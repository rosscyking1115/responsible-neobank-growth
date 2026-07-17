{{ config(
    materialized='incremental',
    unique_key='canonical_event_key',
    incremental_strategy=('merge' if target.type == 'bigquery' else 'delete+insert'),
    partition_by={'field': 'arrival_date', 'data_type': 'date', 'granularity': 'day'},
    cluster_by=['event_type'],
    labels={'project': 'neobank', 'layer': 'normalised'}
) }}

-- Canonical referral lifecycle events with v1/v2 payload adaptation: v1 and
-- v2 qualifications share one canonical meaning; v1 rows expose a null
-- qualification_rule (documented new nullable field, the event-boundary contract).
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
    {{ incremental_ingestion_filter() }}
