select *

from {{ source(
    'morpho',
    'repay_events_enriched'
) }}