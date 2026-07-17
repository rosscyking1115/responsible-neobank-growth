-- Payload validation and quarantine must reconcile: no canonical event may
-- share an event_id with a quarantined delivery.
select deliveries.event_id
from {{ ref('lnd_event_deliveries') }} as deliveries
inner join {{ ref('lnd_event_quarantine') }} as quarantine
    on deliveries.event_id = quarantine.event_id
