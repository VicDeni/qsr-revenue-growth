-- One row per fiscal year: store footprint, US density and how often the 10-K talks about
-- digital/loyalty themes. Shares use the component sum so they stay internally consistent
-- in years where the reported total and the parsed breakdown disagree.
with stores as (
    select * from {{ ref('stg_store_counts') }}
),

us_population as (
    select year as fiscal_year, sum(population) as us_population
    from {{ ref('stg_state_population') }}
    group by 1
),

keywords as (
    select
        fiscal_year,
        {% for kw in ['digital', 'mobile', 'app', 'rewards', 'delivery', 'drive_through', 'china', 'licensed', 'experience'] %}
        max(case when keyword = '{{ kw }}' then per_10k_words end) as {{ kw }}_per_10k{% if not loop.last %},{% endif %}
        {% endfor %}
    from {{ ref('stg_keyword_trends') }}
    group by 1
)

select
    s.fiscal_year,
    s.ceo,
    s.total_stores_reported                                                              as total_stores,
    s.total_stores_reported - lag(s.total_stores_reported) over (order by s.fiscal_year) as net_new_stores,
    round(100 * (s.total_stores_reported
        / lag(s.total_stores_reported) over (order by s.fiscal_year) - 1), 2)            as store_growth_pct,
    s.company_operated_us,
    s.company_operated_international,
    s.licensed_us,
    s.licensed_international,
    s.us_stores,
    s.international_stores,
    round(100 * s.licensed_stores / s.component_sum, 1)                                   as pct_licensed,
    round(100 * s.international_stores / s.component_sum, 1)                              as pct_international,
    s.is_breakdown_complete,
    s.total_stores_reported - s.component_sum                                             as unallocated_stores,
    p.us_population,
    round(s.us_stores / (p.us_population / 1000000.0), 1)                                 as us_stores_per_million,
    k.digital_per_10k,
    k.mobile_per_10k,
    k.app_per_10k,
    k.rewards_per_10k,
    k.delivery_per_10k,
    k.drive_through_per_10k,
    k.china_per_10k,
    k.licensed_per_10k,
    k.experience_per_10k
from stores s
left join us_population p using (fiscal_year)
left join keywords k using (fiscal_year)
