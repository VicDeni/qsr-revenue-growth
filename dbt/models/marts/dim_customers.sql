-- Customer dimension. Age group and gender are stable per customer in the source;
-- channel and rewards status are recorded per order, so they are summarised as shares.
with orders as (
    select * from {{ ref('fct_orders') }}
),

max_date as (
    select max(order_date) as as_of_date from orders
),

agg as (
    select
        customer_id,
        max(age_group)                                                   as age_group,
        max(gender)                                                      as gender,
        count(*)                                                         as orders,
        sum(revenue)                                                     as revenue,
        min(order_date)                                                  as first_order_date,
        max(order_date)                                                  as last_order_date,
        avg(case when is_app_order then 1.0 else 0.0 end)                as app_order_share,
        avg(case when is_rewards_member then 1.0 else 0.0 end)           as rewards_order_share,
        avg(satisfaction_score)                                          as avg_satisfaction
    from orders
    group by 1
)

select
    agg.*,
    revenue / orders                                                     as avg_ticket,
    {{ dbt.datediff('agg.last_order_date', 'max_date.as_of_date', 'day') }} as days_since_last_order,
    case
        when app_order_share = 0   then 'Never uses app'
        when app_order_share < 0.5 then 'Occasional app user'
        else 'App-first'
    end                                                                  as app_adoption_tier
from agg
cross join max_date
