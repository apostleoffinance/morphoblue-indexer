select

    loan_symbol,

    count(*) as repay_events,

    sum(normalized_assets) as total_repaid

from {{ ref('stg_repay_events') }}

group by 1