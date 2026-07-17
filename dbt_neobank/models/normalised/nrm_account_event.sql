{{ config(
    materialized='incremental',
    unique_key='canonical_event_key',
    incremental_strategy=('merge' if target.type == 'bigquery' else 'delete+insert'),
    partition_by={'field': 'arrival_date', 'data_type': 'date', 'granularity': 'day'},
    cluster_by=['event_type'],
    labels={'route_c': 'plan2', 'layer': 'normalised'}
) }}

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
    {{ incremental_ingestion_filter() }}
