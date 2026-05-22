select
    feature_event_id,
    user_id,
    feature_name,
    event_type,
    cast(event_ts as timestamp) as event_ts,
    cast(event_date as date) as event_date,
    region
from read_parquet('{{ var("raw_path", "raw/ci") }}/feature_events.parquet')
