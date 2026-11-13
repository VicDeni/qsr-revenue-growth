{#- Small dialect shims so every model runs unchanged on DuckDB (dev/CI) and BigQuery (prod). -#}

{% macro try_cast(expr, type) -%}
  {{ return(adapter.dispatch('try_cast')(expr, type)) }}
{%- endmacro %}
{% macro default__try_cast(expr, type) -%} try_cast({{ expr }} as {{ type }}) {%- endmacro %}
{% macro bigquery__try_cast(expr, type) -%} safe_cast({{ expr }} as {{ type }}) {%- endmacro %}

{% macro t_double() -%}{{ return(adapter.dispatch('t_double')()) }}{%- endmacro %}
{% macro default__t_double() -%}double{%- endmacro %}
{% macro bigquery__t_double() -%}float64{%- endmacro %}

{% macro t_int() -%}{{ return(adapter.dispatch('t_int')()) }}{%- endmacro %}
{% macro default__t_int() -%}bigint{%- endmacro %}
{% macro bigquery__t_int() -%}int64{%- endmacro %}

{#- 'YYYY-MM-DD' + 'HH:MM' strings -> timestamp without time zone -#}
{% macro make_timestamp(date_str, time_str) -%}
  {{ return(adapter.dispatch('make_timestamp')(date_str, time_str)) }}
{%- endmacro %}
{% macro default__make_timestamp(date_str, time_str) -%}
  try_cast({{ date_str }} || ' ' || {{ time_str }} || ':00' as timestamp)
{%- endmacro %}
{% macro bigquery__make_timestamp(date_str, time_str) -%}
  safe_cast(concat({{ date_str }}, ' ', {{ time_str }}, ':00') as datetime)
{%- endmacro %}

{#- string flag ('True'/'False') -> boolean -#}
{% macro to_bool(expr) -%} (lower({{ expr }}) = 'true') {%- endmacro %}
