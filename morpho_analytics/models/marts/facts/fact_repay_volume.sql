select
    market_id,
    chain,
    loan_symbol,
    sum(amount_normalized) as total_repay_volume,
    sum(amount_usd) as total_repay_volume_usd,
    count(*) as repay_event_count,
    count(distinct wallet_address) as unique_repayers

from {{ ref('stg_repay_events') }}

group by 1, 2, 3
