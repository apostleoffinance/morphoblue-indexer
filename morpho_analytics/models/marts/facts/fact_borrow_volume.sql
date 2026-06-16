select
    market_id,
    chain,
    loan_symbol,
    sum(amount_normalized) as total_borrow_volume,
    sum(amount_usd) as total_borrow_volume_usd,
    count(*) as borrow_event_count,
    count(distinct wallet_address) as unique_borrowers

from {{ ref('stg_borrow_events') }}

group by 1, 2, 3
