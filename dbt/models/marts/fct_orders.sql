-- Order fact table. Incremental: each scheduled run merges only rows loaded since the last run.
{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy=('merge' if target.type == 'bigquery' else 'delete+insert'),
    partition_by=({'field': 'order_date', 'data_type': 'date', 'granularity': 'month'} if target.type == 'bigquery' else none),
    cluster_by=(['order_channel', 'region'] if target.type == 'bigquery' else none),
    on_schema_change='append_new_columns'
) }}

with orders as (

    select * from {{ ref('stg_orders') }}
    {% if is_incremental() %}
    where _loaded_at > (select max(_loaded_at) from {{ this }})
    {% endif %}

)

select
    order_id,
    customer_id,
    store_id,
    order_date,
    cast({{ dbt.date_trunc('month', 'order_date') }} as date)   as order_month,
    order_ts,
    order_hour,
    case
        when order_hour between 5 and 10  then '1. Morning 5-10am'
        when order_hour between 11 and 13 then '2. Midday 11am-1pm'
        when order_hour between 14 and 17 then '3. Afternoon 2-5pm'
        when order_hour between 18 and 21 then '4. Evening 6-9pm'
        else '5. Late night 10pm-4am'
    end                                                         as daypart,
    day_of_week_num,
    day_of_week_name,
    order_channel,
    order_channel = 'Mobile App'                                as is_app_order,
    is_order_ahead,
    store_location_type,
    region,
    age_group,
    gender,
    is_rewards_member,
    drink_category,
    has_food_item,
    items,
    customizations,
    revenue,
    fulfillment_min,
    {{ try_cast('floor(fulfillment_min)', t_int()) }}           as fulfillment_bucket_min,
    satisfaction_score,
    _loaded_at
from orders
