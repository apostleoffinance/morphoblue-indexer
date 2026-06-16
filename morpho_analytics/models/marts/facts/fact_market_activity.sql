with market_keys as (

    select market_id, chain, loan_symbol from {{ ref('fact_supply_volume') }}

    union

    select market_id, chain, loan_symbol from {{ ref('fact_borrow_volume') }}

    union

    select market_id, chain, loan_symbol from {{ ref('fact_repay_volume') }}

    union

    select market_id, chain, loan_symbol from {{ ref('fact_withdraw_volume') }}

),

supply as (

    select * from {{ ref('fact_supply_volume') }}

),

borrow as (

    select * from {{ ref('fact_borrow_volume') }}

),

repay as (

    select * from {{ ref('fact_repay_volume') }}

),

withdraw as (

    select * from {{ ref('fact_withdraw_volume') }}

)

select
    market_keys.market_id,
    market_keys.chain,
    market_keys.loan_symbol,
    coalesce(supply.total_supply_volume, 0) as total_supply_volume,
    coalesce(borrow.total_borrow_volume, 0) as total_borrow_volume,
    coalesce(repay.total_repay_volume, 0) as total_repay_volume,
    coalesce(withdraw.total_withdraw_volume, 0) as total_withdraw_volume,
    coalesce(supply.total_supply_volume, 0) - coalesce(withdraw.total_withdraw_volume, 0) as net_liquidity_flow,
    coalesce(borrow.total_borrow_volume, 0) - coalesce(repay.total_repay_volume, 0) as outstanding_borrow

from market_keys
left join supply
    on market_keys.market_id = supply.market_id
    and market_keys.chain = supply.chain
    and market_keys.loan_symbol is not distinct from supply.loan_symbol
left join borrow
    on market_keys.market_id = borrow.market_id
    and market_keys.chain = borrow.chain
    and market_keys.loan_symbol is not distinct from borrow.loan_symbol
left join repay
    on market_keys.market_id = repay.market_id
    and market_keys.chain = repay.chain
    and market_keys.loan_symbol is not distinct from repay.loan_symbol
left join withdraw
    on market_keys.market_id = withdraw.market_id
    and market_keys.chain = withdraw.chain
    and market_keys.loan_symbol is not distinct from withdraw.loan_symbol
