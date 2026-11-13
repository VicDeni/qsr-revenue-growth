-- "McDonald's FY2025" -> company = McDonald's, fiscal_year = 2025; one row per document x keyword.
with source as (
    select * from {{ source('raw', 'competitor_keywords') }}
)

{% for kw in var('competitor_keywords') %}
select
    document,
    trim({{ dbt.split_part('document', "' FY'", 1) }})                       as company,
    {{ try_cast(dbt.split_part('document', "' FY'", 2), t_int()) }}           as fiscal_year,
    {{ try_cast('total_words', t_int()) }}                                    as total_words,
    '{{ kw }}'                                                                as keyword,
    {{ try_cast(kw, t_double()) }}                                            as per_10k_words
from source
{% if not loop.last %}union all{% endif %}
{% endfor %}
