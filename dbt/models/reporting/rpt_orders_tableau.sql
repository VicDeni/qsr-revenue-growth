-- One wide, order-level table for self-serve BI (Tableau / Looker Studio).
-- Field names are made business-friendly by the export step.
select
    f.order_id,
    f.order_date,
    f.order_month,
    f.order_ts,
    f.order_hour,
    f.daypart,
    f.day_of_week_num,
    f.day_of_week_name,
    f.order_channel,
    f.is_app_order,
    f.is_order_ahead,
    f.store_id,
    f.store_location_type,
    f.region,
    f.customer_id,
    f.age_group,
    f.gender,
    c.app_adoption_tier         as customer_app_adoption,
    f.is_rewards_member,
    f.drink_category,
    f.has_food_item,
    f.items,
    f.customizations,
    f.revenue,
    f.fulfillment_min,
    f.fulfillment_bucket_min,
    f.satisfaction_score
from {{ ref('fct_orders') }} f
left join {{ ref('dim_customers') }} c using (customer_id)
