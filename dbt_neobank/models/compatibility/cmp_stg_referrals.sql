-- Compatibility view: stg_referrals' core contract served from the governed
-- referral_economics interface. Reward amounts convert from integer minor
-- units to the legacy GBP floats at this boundary only (display conversion,
-- not a second source of truth). Geo columns are not served by the event
-- boundary; declared in compatibility.yml.
select
    referral_id,
    referrer_customer_id as referrer_user_id,
    referred_customer_id as referee_user_id,
    invited_at as created_at,
    cast(invited_at as date) as created_date,
    is_qualified,
    referred_customer_funded,
    lifecycle_status,
    booked_minor / 100.0 as referrer_reward_gbp
from {{ ref('prs_referral_economics') }}
