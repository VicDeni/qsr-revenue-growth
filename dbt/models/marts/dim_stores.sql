select
    store_id,
    max(region)                 as region,
    max(store_location_type)    as store_location_type,
    count(*)                    as orders,
    sum(revenue)                as revenue,
    min(order_date)             as first_order_date,
    max(order_date)             as last_order_date
from {{ ref('fct_orders') }}
group by 1
