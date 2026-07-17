-- A customer must hold exactly one variant per experiment (assignment stability).
select experiment_id, customer_id
from {{ ref('nrm_experiment_assignment') }}
group by experiment_id, customer_id
having count(distinct variant) > 1
