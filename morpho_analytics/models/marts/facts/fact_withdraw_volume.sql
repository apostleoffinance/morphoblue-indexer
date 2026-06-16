select
    market_id,
    chain,
    loan_symbol,
    sum(amount_normalized) as total_withdraw_volume,
    count(*) as withdraw_event_count,
    count(distinct wallet_address) as unique_withdrawers

from {{ ref('stg_withdraw_events') }}

group by 1, 2, 3
