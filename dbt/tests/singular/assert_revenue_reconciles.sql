-- Every order and every cent in staging must reach the reporting table.
with s as (select count(*) as n, round(sum(revenue), 2) as revenue from {{ ref('stg_orders') }}),
     r as (select count(*) as n, round(sum(revenue), 2) as revenue from {{ ref('rpt_orders_tableau') }})
select s.n as stg_orders, r.n as rpt_orders, s.revenue as stg_revenue, r.revenue as rpt_revenue
from s cross join r
where s.n != r.n or abs(s.revenue - r.revenue) > 0.01
