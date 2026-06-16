select
    loan_symbol,
    sum(total_supply_volume) as total_supply,
    sum(total_supply_volume_usd) as total_supply_usd

from {{ ref('fact_supply_volume') }}

group by loan_symbol
