with source as (

    select * from {{ source('morpho', 'withdraw_events_enriched') }}

),

cleaned as (

    select
        chain,
        event as event_type,
        {{ normalize_address('address') }} as contract_address,
        block_number::bigint as block_number,
        cast(block_timestamp as timestamp) as event_timestamp,
        {{ normalize_address('block_hash') }} as block_hash,
        {{ normalize_address('transaction_hash') }} as transaction_hash,
        transaction_index::integer as transaction_index,
        log_index::integer as log_index,
        transaction_log_index::integer as transaction_log_index,
        {{ normalize_address('on_behalf') }} as wallet_address,
        {{ normalize_address('caller') }} as caller_address,
        {{ normalize_address('receiver') }} as receiver_address,
        assets as amount_raw,
        shares as shares_raw,
        {{ normalize_address('market_id') }} as market_id,
        {{ normalize_address('loan_token') }} as loan_token,
        {{ normalize_address('collateral_token') }} as collateral_token,
        loan_symbol,
        collateral_symbol,
        loan_decimals::integer as loan_decimals,
        normalized_assets::numeric as amount_normalized,
        price_usd::numeric as price_usd,
        amount_usd::numeric as amount_usd

    from source

)

select * from cleaned
