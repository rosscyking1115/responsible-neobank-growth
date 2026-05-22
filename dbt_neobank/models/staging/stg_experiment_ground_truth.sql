select
    metric,
    cast(value as double) as value,
    description
from read_parquet('{{ var("raw_path", "raw/ci") }}/experiment_ground_truth.parquet')
