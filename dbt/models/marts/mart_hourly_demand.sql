-- Weekday x hour demand grid (for staffing and daypart analysis).
select
    day_of_week_num,
    day_of_week_name,
    order_hour,
    daypart,
    order_channel,
    count(*)            as orders,
    sum(revenue)        as revenue
from {{ ref('fct_orders') }}
group by 1, 2, 3, 4, 5
