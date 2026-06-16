with supplier_volumes as (

    select
        market_id,
        chain,
        loan_symbol,
        wallet_address,
        sum(amount_normalized) as supplier_supply_volume

    from {{ ref('stg_supply_events') }}

    where wallet_address is not null
        and amount_normalized is not null

    group by 1, 2, 3, 4

),

market_totals as (

    select
        market_id,
        chain,
        loan_symbol,
        sum(supplier_supply_volume) as total_supply,
        count(distinct wallet_address) as unique_suppliers

    from supplier_volumes

    group by 1, 2, 3

),

ranked_suppliers as (

    select
        market_id,
        chain,
        loan_symbol,
        wallet_address,
        supplier_supply_volume,
        row_number() over (
            partition by market_id, chain, loan_symbol
            order by supplier_supply_volume desc
        ) as supplier_rank

    from supplier_volumes

),

largest_supplier as (

    select
        market_id,
        chain,
        loan_symbol,
        supplier_supply_volume as largest_supplier_supply

    from ranked_suppliers

    where supplier_rank = 1

),

top_five_suppliers as (

    select
        market_id,
        chain,
        loan_symbol,
        sum(supplier_supply_volume) as top_5_supplier_supply

    from ranked_suppliers

    where supplier_rank <= 5

    group by 1, 2, 3

)

select
    market_totals.market_id,
    market_totals.chain,
    market_totals.loan_symbol,
    market_totals.total_supply,
    largest_supplier.largest_supplier_supply,
    case
        when market_totals.total_supply > 0
            then largest_supplier.largest_supplier_supply / market_totals.total_supply
        else null
    end as largest_supplier_pct,
    case
        when market_totals.total_supply > 0
            then top_five_suppliers.top_5_supplier_supply / market_totals.total_supply
        else null
    end as top_5_supplier_pct,
    market_totals.unique_suppliers

from market_totals
left join largest_supplier
    on market_totals.market_id = largest_supplier.market_id
    and market_totals.chain = largest_supplier.chain
    and market_totals.loan_symbol is not distinct from largest_supplier.loan_symbol
left join top_five_suppliers
    on market_totals.market_id = top_five_suppliers.market_id
    and market_totals.chain = top_five_suppliers.chain
    and market_totals.loan_symbol is not distinct from top_five_suppliers.loan_symbol
