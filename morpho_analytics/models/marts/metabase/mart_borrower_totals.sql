select
    wallet_address as borrower,
    sum(amount_normalized) as borrowed,
    sum(amount_usd) as borrowed_usd

from {{ ref('stg_borrow_events') }}

group by wallet_address
