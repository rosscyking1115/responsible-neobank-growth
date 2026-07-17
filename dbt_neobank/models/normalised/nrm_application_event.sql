{{ config(
    materialized='incremental',
    unique_key='canonical_event_key',
    incremental_strategy=('merge' if target.type == 'bigquery' else 'delete+insert'),
    partition_by={'field': 'arrival_date', 'data_type': 'date', 'granularity': 'day'},
    cluster_by=['event_type'],
    labels={'route_c': 'plan2', 'layer': 'normalised'}
) }}

-- Canonical, version-independent application/KYC events: one row per
-- canonical business event (duplicates suppressed at landing).
select
    idempotency_key as canonical_event_key,
    event_id,
    replace(event_name, '-', '_') as event_type,
    application_id,
    customer_id,
    channel,
    campaign_id,
    referral_id,
    requested_product,
    decision,
    decision_source,
    occurred_at,
    ingested_at,
    arrival_date
from {{ ref('lnd_application_events') }}
where is_canonical
    {{ incremental_ingestion_filter() }}
