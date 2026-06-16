select
    wallet_address as supplier,
    sum(amount_normalized) as supplied,
    sum(amount_usd) as supplied_usd

from {{ ref('stg_supply_events') }}

group by wallet_address
