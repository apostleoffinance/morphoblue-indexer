with markets as (

    select
        chain,
        {{ normalize_address('market_id') }} as market_id,
        {{ normalize_address('loan_token') }} as loan_token,
        {{ normalize_address('collateral_token') }} as collateral_token,
        lltv::numeric as lltv

    from {{ source('morpho', 'market_lookup') }}

),

tokens as (

    select
        chain,
        {{ normalize_address('token_address') }} as token_address,
        symbol,
        decimals::integer as decimals

    from {{ source('morpho', 'token_lookup') }}

),

enriched as (

    select
        markets.chain,
        markets.market_id,
        markets.loan_token,
        markets.collateral_token,
        loan_tokens.symbol as loan_symbol,
        collateral_tokens.symbol as collateral_symbol,
        loan_tokens.decimals as loan_decimals,
        markets.lltv

    from markets
    left join tokens as loan_tokens
        on markets.chain = loan_tokens.chain
        and markets.loan_token = loan_tokens.token_address
    left join tokens as collateral_tokens
        on markets.chain = collateral_tokens.chain
        and markets.collateral_token = collateral_tokens.token_address

)

select * from enriched
