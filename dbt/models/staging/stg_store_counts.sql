-- Store counts by fiscal year. The four ownership x geography components should sum to the
-- reported total; years where the 10-K table parse was partial are flagged, not hidden.
with source as (
    select * from {{ source('raw', 'store_counts') }}
),

typed as (
    select
        {{ try_cast('fiscal_year', t_int()) }}       as fiscal_year,
        {{ try_cast('co_us', t_int()) }}             as company_operated_us,
        {{ try_cast('co_international', t_int()) }}  as company_operated_international,
        {{ try_cast('lic_us', t_int()) }}            as licensed_us,
        {{ try_cast('lic_international', t_int()) }} as licensed_international,
        {{ try_cast('total_worldwide', t_int()) }}   as total_stores_reported,
        ceo,
        source_note
    from source
)

select
    *,
    company_operated_us + company_operated_international + licensed_us + licensed_international as component_sum,
    company_operated_us + licensed_us                                                     as us_stores,
    company_operated_international + licensed_international                               as international_stores,
    company_operated_us + company_operated_international                                  as company_operated_stores,
    licensed_us + licensed_international                                                  as licensed_stores,
    (company_operated_us + company_operated_international + licensed_us + licensed_international)
        = total_stores_reported                                                           as is_breakdown_complete
from typed
