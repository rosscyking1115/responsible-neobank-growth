select
    metric,
    cast(value as {{ float_type() }}) as value,
    description
from {{ raw_table('experiment_ground_truth', 'experiment_ground_truth.parquet') }}
