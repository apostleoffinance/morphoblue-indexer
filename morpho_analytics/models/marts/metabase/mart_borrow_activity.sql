select
    loan_symbol,
    sum(total_borrow_volume) as total_borrow,
    sum(total_borrow_volume_usd) as total_borrow_usd

from {{ ref('fact_borrow_volume') }}

group by loan_symbol
