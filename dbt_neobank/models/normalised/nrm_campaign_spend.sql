{{ config(
    materialized='incremental',
    unique_key='canonical_event_key',
    incremental_strategy=('merge' if target.type == 'bigquery' else 'delete+insert'),
    partition_by={'field': 'arrival_date', 'data_type': 'date', 'granularity': 'day'},
    cluster_by=['campaign_id'],
    labels={'route_c': 'plan2', 'layer': 'normalised'}
) }}

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
    {{ incremental_ingestion_filter() }}
