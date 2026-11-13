-- Daily demand by channel; additive measures only so any roll-up stays correct.
select
    order_date,
    day_of_week_num,
    day_of_week_name,
    order_channel,
    count(*)                                            as orders,
    sum(revenue)                                        as revenue,
    sum(items)                                          as items,
    sum(customizations)                                 as customizations,
    sum(case when has_food_item then 1 else 0 end)      as food_orders,
    sum(satisfaction_score)                             as satisfaction_total,
    sum(fulfillment_min)                                as fulfillment_min_total
from {{ ref('fct_orders') }}
group by 1, 2, 3, 4
