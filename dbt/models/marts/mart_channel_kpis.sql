-- Channel scorecard. Shares are of all orders / all revenue in the warehouse.
with by_channel as (
    select
        order_channel,
        count(*)                                                    as orders,
        sum(revenue)                                                as revenue,
        sum(items)                                                  as items,
        sum(customizations)                                         as customizations,
        sum(case when has_food_item then 1 else 0 end)              as food_orders,
        sum(case when is_rewards_member then 1 else 0 end)          as rewards_orders,
        sum(fulfillment_min)                                        as fulfillment_min_total,
        sum(satisfaction_score)                                     as satisfaction_total
    from {{ ref('fct_orders') }}
    group by 1
),

totals as (
    select sum(orders) as all_orders, sum(revenue) as all_revenue from by_channel
)

select
    c.order_channel,
    c.orders,
    round(c.revenue, 2)                                  as revenue,
    round(c.orders / t.all_orders, 4)                    as order_share,
    round(c.revenue / t.all_revenue, 4)                  as revenue_share,
    round(c.revenue / c.orders, 2)                       as avg_ticket,
    round(c.items / c.orders, 2)                         as items_per_order,
    round(c.customizations / c.orders, 2)                as customizations_per_order,
    round(c.food_orders / c.orders, 4)                   as food_attach_rate,
    round(c.rewards_orders / c.orders, 4)                as rewards_order_share,
    round(c.fulfillment_min_total / c.orders, 2)         as avg_fulfillment_min,
    round(c.satisfaction_total / c.orders, 3)            as avg_satisfaction
from by_channel c
cross join totals t
