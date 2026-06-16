with tokens as (

    select
        chain,
        {{ normalize_address('token_address') }} as token_address,
        symbol,
        name,
        decimals::integer as decimals

    from {{ source('morpho', 'token_lookup') }}

)

select * from tokens
