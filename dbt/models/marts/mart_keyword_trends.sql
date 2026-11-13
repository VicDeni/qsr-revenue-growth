select
    k.fiscal_year,
    k.keyword,
    k.mentions,
    k.per_10k_words,
    s.ceo
from {{ ref('stg_keyword_trends') }} k
left join {{ ref('stg_store_counts') }} s using (fiscal_year)
