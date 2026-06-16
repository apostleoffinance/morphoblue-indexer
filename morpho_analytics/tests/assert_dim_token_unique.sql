-- Fail if duplicate (chain, token_address) pairs exist in dim_token.
select
    chain,
    token_address,
    count(*) as row_count

from {{ ref('dim_token') }}

group by 1, 2

having count(*) > 1
