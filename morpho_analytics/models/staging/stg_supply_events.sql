select *

from {{ source(
    'morpho',
    'supply_events_enriched'
) }}