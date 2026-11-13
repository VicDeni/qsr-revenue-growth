select company, fiscal_year, document, keyword, per_10k_words, total_words
from {{ ref('stg_competitor_keywords') }}
