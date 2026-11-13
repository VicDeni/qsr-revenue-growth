-- Warn (not fail) when a year's company-operated/licensed x US/international breakdown does not
-- sum to the reported total. Known cause: partial table parsing in the FY2012-FY2019 10-Ks.
{{ config(severity='warn') }}
select fiscal_year, total_stores_reported, component_sum, total_stores_reported - component_sum as gap
from {{ ref('stg_store_counts') }}
where not is_breakdown_complete
