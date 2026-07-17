-- Daily reward reconciliation: one row per qualified referral per warehouse
-- activity day from its qualification arrival onward, with cumulative
-- positions (by arrival, i.e. what the warehouse knew that day), lifecycle
-- status, balance check and exception reason codes.
--
-- Grain note: days are warehouse activity days (distinct arrival dates), not a
-- full calendar spine; partition-by-day replacement is the intended BigQuery
-- strategy. Reason codes are append-only.
with days as (
    select distinct arrival_date as reconciliation_date
    from {{ ref('lnd_event_deliveries') }}
),

entitlements as (
    select
        referral_id,
        reward_id,
        qualified_arrival_date,
        entitled_minor
    from {{ ref('lgl_reward_entitlement') }}
),

grid as (
    select
        entitlements.referral_id,
        entitlements.reward_id,
        entitlements.entitled_minor,
        entitlements.qualified_arrival_date,
        days.reconciliation_date
    from entitlements
    inner join days on days.reconciliation_date >= entitlements.qualified_arrival_date
),

reward_events as (
    select *
    from {{ ref('nrm_reward_event') }}
    where referral_id is not null
),

positions as (
    select
        grid.referral_id,
        grid.reward_id,
        grid.entitled_minor,
        grid.qualified_arrival_date,
        grid.reconciliation_date,
        count(case when reward_events.event_type = 'reward_booked' then 1 end)
            as booking_count,
        coalesce(sum(case when reward_events.event_type = 'reward_booked'
            then reward_events.amount_minor end), 0) as booked_minor,
        coalesce(sum(case when reward_events.event_type = 'reward_settled'
            then reward_events.amount_minor end), 0) as settled_minor,
        coalesce(sum(case when reward_events.event_type = 'reward_reversed'
            then reward_events.amount_minor end), 0) as reversed_minor,
        min(case when reward_events.event_type = 'reward_booked'
            then reward_events.arrival_date end) as booked_arrival_date
    from grid
    left join reward_events
        on reward_events.referral_id = grid.referral_id
        and reward_events.arrival_date <= grid.reconciliation_date
    group by 1, 2, 3, 4, 5
),

ledger_balance as (
    select
        grid.referral_id,
        grid.reconciliation_date,
        coalesce(sum(case when entries.entry_side = 'debit'
            then entries.amount_minor end), 0) as debit_minor,
        coalesce(sum(case when entries.entry_side = 'credit'
            then entries.amount_minor end), 0) as credit_minor
    from grid
    left join {{ ref('nrm_reward_ledger_entry') }} as entries
        on entries.referral_id = grid.referral_id
        and entries.arrival_date <= grid.reconciliation_date
    group by 1, 2
)

select
    positions.referral_id,
    positions.reward_id,
    positions.reconciliation_date,
    positions.entitled_minor,
    positions.booked_minor,
    positions.settled_minor,
    positions.reversed_minor,
    positions.booked_minor - positions.settled_minor - positions.reversed_minor
        as outstanding_payable_minor,
    case
        when positions.reversed_minor > 0 then 'reversed'
        when positions.settled_minor >= positions.booked_minor
            and positions.booked_minor > 0 then 'settled'
        when positions.booked_minor > 0 then 'booked'
        else 'qualified'
    end as lifecycle_status,
    ledger_balance.debit_minor,
    ledger_balance.credit_minor,
    ledger_balance.debit_minor = ledger_balance.credit_minor as is_balanced,
    case
        when positions.booking_count = 0 then 'missing_posting'
        when positions.booking_count > 1 then 'duplicate_posting'
        when positions.booked_minor != positions.entitled_minor then 'amount_mismatch'
        when positions.settled_minor > 0 and positions.booked_minor = 0
            then 'settlement_without_booking'
        when positions.reversed_minor > positions.booked_minor
            then 'reversal_beyond_booked_amount'
        when ledger_balance.debit_minor != ledger_balance.credit_minor
            then 'unbalanced_journal'
        when positions.booked_minor > 0
            and positions.settled_minor = 0
            and positions.reversed_minor = 0
            and {{ date_diff_days(
                'positions.reconciliation_date', 'positions.booked_arrival_date'
            ) }} > {{ var('reward_settlement_sla_days') }}
            then 'pending_beyond_synthetic_sla'
    end as exception_reason,
    case
        when positions.booking_count = 0
            then {{ date_diff_days(
                'positions.reconciliation_date', 'positions.qualified_arrival_date'
            ) }}
    end as exception_age_days
from positions
inner join ledger_balance
    on positions.referral_id = ledger_balance.referral_id
    and positions.reconciliation_date = ledger_balance.reconciliation_date
