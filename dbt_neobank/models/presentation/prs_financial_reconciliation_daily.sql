-- Daily reconciliation rollup for Finance reporting and the future
-- reward_reconciliation Looker Explore. One row per reconciliation day.
select
    reconciliation_date,
    count(*) as entitlements,
    sum(entitled_minor) as entitled_minor,
    sum(booked_minor) as booked_minor,
    sum(settled_minor) as settled_minor,
    sum(reversed_minor) as reversed_minor,
    sum(outstanding_payable_minor) as outstanding_payable_minor,
    sum(entitled_minor) - sum(booked_minor) as entitlement_variance_minor,
    sum(case when not is_balanced then 1 else 0 end) as unbalanced_referrals,
    sum(case when exception_reason is not null then 1 else 0 end) as exception_count,
    sum(case when exception_reason = 'missing_posting' then 1 else 0 end)
        as missing_posting_count,
    sum(case when exception_reason = 'duplicate_posting' then 1 else 0 end)
        as duplicate_posting_count,
    sum(case when exception_reason = 'amount_mismatch' then 1 else 0 end)
        as amount_mismatch_count,
    sum(case when exception_reason = 'settlement_without_booking' then 1 else 0 end)
        as settlement_without_booking_count,
    sum(case when exception_reason = 'reversal_beyond_booked_amount' then 1 else 0 end)
        as reversal_beyond_booked_count,
    sum(case when exception_reason = 'unbalanced_journal' then 1 else 0 end)
        as unbalanced_journal_count,
    sum(case when exception_reason = 'pending_beyond_synthetic_sla' then 1 else 0 end)
        as pending_beyond_sla_count
from {{ ref('lgl_reward_ledger_reconciliation') }}
group by reconciliation_date
