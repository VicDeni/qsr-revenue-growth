-- Long format: one row per fiscal year x keyword (wide source has <kw> and <kw>_per10k columns).
with source as (
    select * from {{ source('raw', 'keyword_trends') }}
)

{% for kw in var('strategy_keywords') %}
select
    {{ try_cast('fiscal_year', t_int()) }}        as fiscal_year,
    '{{ kw }}'                                    as keyword,
    {{ try_cast(kw, t_int()) }}                   as mentions,
    {{ try_cast(kw ~ '_per10k', t_double()) }}    as per_10k_words,
    {{ try_cast('total_words', t_int()) }}        as total_words
from source
{% if not loop.last %}union all{% endif %}
{% endfor %}
