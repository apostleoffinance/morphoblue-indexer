select
    market_id,
    chain,
    loan_symbol,
    total_borrow_volume as total_borrow,
    total_repay_volume as total_repay,
    total_borrow_volume - total_repay_volume as outstanding_borrow,
    case
        when total_borrow_volume > 0
            then total_repay_volume / total_borrow_volume
        else null
    end as repayment_ratio

from {{ ref('fact_market_activity') }}
