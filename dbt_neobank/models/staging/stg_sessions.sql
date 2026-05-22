select
    session_id,
    user_id,
    cast(started_at as timestamp) as started_at,
    cast(started_date as date) as started_date,
    region,
    device_os,
    cast(duration_seconds as integer) as duration_seconds,
    cast(app_crashed as boolean) as app_crashed
from read_parquet('{{ var("raw_path", "raw/ci") }}/sessions.parquet')
