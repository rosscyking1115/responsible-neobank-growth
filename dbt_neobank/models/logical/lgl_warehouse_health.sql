-- Governed interface: warehouse_health (contracts/interfaces/warehouse-health.yml).
-- One row per governed interface per warehouse activity day with local
-- freshness and volume evidence. BigQuery bytes, slot and cost fields remain
-- null until Plan 3 supplies dated measurements — nulls are never displayed as
-- zero cost.
with interface_families as (
    select 'growth_acquisition' as model_name, 'application-submitted' as event_name
    union all select 'growth_acquisition', 'kyc-decisioned'
    union all select 'growth_acquisition', 'account-activated'
    union all select 'growth_acquisition', 'account-funded'
    union all select 'growth_acquisition', 'experiment-assigned'
    union all select 'growth_acquisition', 'customer-outcome-recorded'
    union all select 'referral_economics', 'referral-invited'
    union all select 'referral_economics', 'referral-qualified'
    union all select 'referral_economics', 'reward-booked'
    union all select 'reward_reconciliation', 'reward-booked'
    union all select 'reward_reconciliation', 'reward-settled'
    union all select 'reward_reconciliation', 'reward-reversed'
),

days as (
    select distinct arrival_date as run_date
    from {{ ref('lnd_event_deliveries') }}
),

daily_deliveries as (
    select
        interface_families.model_name,
        deliveries.arrival_date as run_date,
        count(*) as deliveries_ingested,
        max(deliveries.ingested_at) as last_ingested_at
    from {{ ref('lnd_event_deliveries') }} as deliveries
    inner join interface_families
        on deliveries.event_name = interface_families.event_name
    group by 1, 2
),

daily_quarantine as (
    select
        interface_families.model_name,
        quarantine.arrival_date as run_date,
        count(*) as deliveries_quarantined
    from {{ ref('lnd_event_quarantine') }} as quarantine
    inner join interface_families
        on quarantine.event_name = interface_families.event_name
    group by 1, 2
),

grid as (
    select distinct interface_families.model_name, days.run_date
    from interface_families
    cross join days
),

with_freshness as (
    select
        grid.model_name,
        grid.run_date,
        coalesce(daily_deliveries.deliveries_ingested, 0) as deliveries_ingested,
        coalesce(daily_quarantine.deliveries_quarantined, 0) as deliveries_quarantined,
        max(daily_deliveries.last_ingested_at) over (
            partition by grid.model_name
            order by grid.run_date
            rows between unbounded preceding and current row
        ) as freshest_ingested_at
    from grid
    left join daily_deliveries
        on grid.model_name = daily_deliveries.model_name
        and grid.run_date = daily_deliveries.run_date
    left join daily_quarantine
        on grid.model_name = daily_quarantine.model_name
        and grid.run_date = daily_quarantine.run_date
)

select
    model_name,
    run_date,
    'platform' as owner,
    deliveries_ingested,
    deliveries_quarantined,
    freshest_ingested_at,
    {{ date_diff_days('run_date', 'cast(freshest_ingested_at as date)') }}
        as days_since_last_arrival,
    case
        when {{ date_diff_days('run_date', 'cast(freshest_ingested_at as date)') }} >= 3
            then 'error'
        when {{ date_diff_days('run_date', 'cast(freshest_ingested_at as date)') }} >= 1
            then 'warn'
        else 'fresh'
    end as freshness_status,
    -- Plan 3 measurement fields: null until a dated BigQuery run exists.
    cast(null as {{ string_type() }}) as strategy,
    cast(null as bigint) as bytes_processed,
    cast(null as bigint) as bytes_billed,
    cast(null as bigint) as total_slot_ms,
    cast(null as {{ float_type() }}) as estimated_cost,
    cast(null as {{ string_type() }}) as pricing_date
from with_freshness
