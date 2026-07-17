-- Reward family deliveries (booked/settled/reversed) with payload fields
-- flattened. Referral resolution for settlements/reversals happens in
-- nrm_reward_event.
select
    event_id,
    idempotency_key,
    event_name,
    occurred_at,
    emitted_at,
    ingested_at,
    schema_version,
    trace_id,
    arrival_date,
    is_canonical,
    {{ json_value('payload', 'reward_id') }} as reward_id,
    {{ json_value('payload', 'referral_id') }} as referral_id,
    {{ json_value('payload', 'beneficiary_customer_id') }} as beneficiary_customer_id,
    {{ json_value('payload', 'settlement_id') }} as settlement_id,
    {{ json_value('payload', 'reversal_id') }} as reversal_id,
    cast({{ json_value('payload', 'amount_minor') }} as {{ integer_type() }}) as amount_minor,
    {{ json_value('payload', 'currency') }} as currency,
    {{ json_value('payload', 'reversal_reason') }} as reversal_reason
from {{ ref('lnd_event_deliveries') }}
where event_name in ('reward-booked', 'reward-settled', 'reward-reversed')
