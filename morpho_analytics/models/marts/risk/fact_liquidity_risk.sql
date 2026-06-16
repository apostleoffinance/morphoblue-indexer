select
    market_id,
    chain,
    loan_symbol,
    total_supply_volume as total_supply,
    total_withdraw_volume as total_withdraw,
    case
        when total_supply_volume > 0
            then total_withdraw_volume / total_supply_volume
        else null
    end as withdrawal_ratio,
    total_supply_volume - total_withdraw_volume as net_liquidity

from {{ ref('fact_market_activity') }}
