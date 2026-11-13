{#- Same idea as dbt_utils.unique_combination_of_columns, without needing a package download. -#}
{% test dbt_utils_free_unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
