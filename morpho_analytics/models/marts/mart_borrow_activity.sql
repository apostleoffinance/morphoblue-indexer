select

    loan_symbol,

    count(*) as borrow_events,

    sum(normalized_assets) as total_borrow

from {{ ref('stg_borrow_events') }}

group by 1