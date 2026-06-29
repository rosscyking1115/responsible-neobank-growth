select
    user_id,
    cast(identity_check_started as boolean) as identity_check_started,
    cast(identity_check_passed as boolean) as identity_check_passed,
    cast(card_activated as boolean) as card_activated,
    cast(completed_onboarding as boolean) as completed_onboarding,
    furthest_step,
    abandoned_step,
    cast(needs_assisted_onboarding as boolean) as needs_assisted_onboarding
from {{ raw_table('onboarding_events', 'onboarding_events.parquet') }}
