select
    experiment_name,
    user_id,
    variant,
    cast(assignment_bucket as {{ integer_type() }}) as assignment_bucket,
    cast(assigned_at as timestamp) as assigned_at,
    cast(experiment_start_ts as timestamp) as experiment_start_ts,
    cast(experiment_end_ts as timestamp) as experiment_end_ts,
    cast(true_d7_lift_pp as {{ float_type() }}) as true_d7_lift_pp
from {{ raw_table('experiment_assignments', 'experiment_assignments.parquet') }}
