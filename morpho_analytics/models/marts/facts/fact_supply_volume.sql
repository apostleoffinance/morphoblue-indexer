select
    market_id,
    chain,
    loan_symbol,
    sum(amount_normalized) as total_supply_volume,
    sum(amount_usd) as total_supply_volume_usd,
    count(*) as supply_event_count,
    count(distinct wallet_address) as unique_suppliers

from {{ ref('stg_supply_events') }}

group by 1, 2, 3
