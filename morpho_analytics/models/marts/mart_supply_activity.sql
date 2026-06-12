select

    loan_symbol,

    count(*) as supply_events,

    sum(normalized_assets) as total_supply

from {{ ref('stg_supply_events') }}

group by 1