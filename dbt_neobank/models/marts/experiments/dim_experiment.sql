select
    experiment_name,
    min(experiment_start_ts) as first_assignment_ts,
    max(experiment_end_ts) as last_assignment_ts,
    count(*) as assigned_users,
    sum(case when variant = 'treatment' then 1 else 0 end) as treatment_users,
    sum(case when variant = 'control' then 1 else 0 end) as control_users
from {{ ref('stg_experiment_assignments') }}
group by 1
