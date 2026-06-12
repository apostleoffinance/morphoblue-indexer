select

    loan_symbol,

    count(*) as withdraw_events,

    sum(normalized_assets) as total_withdrawn

from {{ ref('stg_withdraw_events') }}

group by 1