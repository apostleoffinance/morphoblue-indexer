select *

from {{ source(
    'morpho',
    'borrow_events_enriched'
) }}