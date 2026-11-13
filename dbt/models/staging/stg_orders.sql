-- One row per order: typed, deduplicated (latest load wins), with clean names.
with source as (

    select * from {{ source('raw', 'orders') }}
    where order_id is not null
    qualify row_number() over (partition by order_id order by _loaded_at desc, _row_number desc) = 1

)

select
    order_id,
    customer_id,
    store_id,
    {{ try_cast('order_date', 'date') }}                                   as order_date,
    {{ make_timestamp('order_date', 'order_time') }}                       as order_ts,
    {{ try_cast('substr(order_time, 1, 2)', t_int()) }}                    as order_hour,
    day_of_week                                                            as day_of_week_name,
    case day_of_week
        when 'Mon' then 1 when 'Tue' then 2 when 'Wed' then 3 when 'Thu' then 4
        when 'Fri' then 5 when 'Sat' then 6 when 'Sun' then 7
    end                                                                    as day_of_week_num,
    order_channel,
    store_location_type,
    region,
    customer_age_group                                                     as age_group,
    customer_gender                                                        as gender,
    {{ to_bool('is_rewards_member') }}                                     as is_rewards_member,
    drink_category,
    {{ to_bool('has_food_item') }}                                         as has_food_item,
    {{ to_bool('order_ahead') }}                                           as is_order_ahead,
    {{ try_cast('cart_size', t_int()) }}                                   as items,
    {{ try_cast('num_customizations', t_int()) }}                          as customizations,
    {{ try_cast('total_spend', t_double()) }}                              as revenue,
    {{ try_cast('fulfillment_time_min', t_double()) }}                     as fulfillment_min,
    {{ try_cast('customer_satisfaction', t_int()) }}                       as satisfaction_score,
    _source_file,
    _loaded_at
from source
