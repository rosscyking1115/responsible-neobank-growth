-- Daily warehouse-health rollup (Monitoring tab and the future
-- warehouse_health Looker Explore). Cost fields stay null until Plan 3
-- supplies measurements; nulls must never be rendered as zero cost.
select
    model_name,
    run_date,
    owner,
    deliveries_ingested,
    deliveries_quarantined,
    freshest_ingested_at,
    days_since_last_arrival,
    freshness_status,
    strategy,
    bytes_processed,
    bytes_billed,
    total_slot_ms,
    estimated_cost,
    pricing_date
from {{ ref('lgl_warehouse_health') }}
