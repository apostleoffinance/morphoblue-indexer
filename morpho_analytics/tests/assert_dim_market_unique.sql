-- Fail if duplicate (chain, market_id) pairs exist in dim_market.
select
    chain,
    market_id,
    count(*) as row_count

from {{ ref('dim_market') }}

group by 1, 2

having count(*) > 1
