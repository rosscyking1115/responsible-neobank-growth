{{ config(
    materialized='incremental',
    unique_key='canonical_event_key',
    incremental_strategy='delete+insert'
) }}

-- Canonical experiment assignments: one stable variant per customer per
-- experiment (assignment stability tested).
select
    idempotency_key as canonical_event_key,
    event_id,
    experiment_id,
    customer_id,
    variant,
    assignment_unit,
    occurred_at,
    ingested_at,
    arrival_date
from {{ ref('lnd_experiment_events') }}
where is_canonical
    {{ incremental_ingestion_filter() }}
