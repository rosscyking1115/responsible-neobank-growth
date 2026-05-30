select
    feature_event_id,
    user_id,
    feature_name,
    event_type,
    cast(event_ts as timestamp) as event_ts,
    cast(event_date as date) as event_date,
    region
from {{ raw_table('feature_events', 'feature_events.parquet') }}
