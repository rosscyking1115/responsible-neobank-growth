{{ config(
    materialized='incremental',
    unique_key='canonical_event_key',
    incremental_strategy=('merge' if target.type == 'bigquery' else 'delete+insert'),
    partition_by={'field': 'arrival_date', 'data_type': 'date', 'granularity': 'day'},
    cluster_by=['outcome_type'],
    labels={'route_c': 'plan2', 'layer': 'normalised'}
) }}

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
    {{ incremental_ingestion_filter() }}
