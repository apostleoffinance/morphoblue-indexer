select *

from {{ source(
    'morpho',
    'withdraw_events_enriched'
) }}