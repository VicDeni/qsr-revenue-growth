{#- Keep dbt's default naming (<target schema>_<custom schema>, e.g. qsr_marts) on every target. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
  {%- if custom_schema_name is none -%}{{ target.schema }}{%- else -%}{{ target.schema }}_{{ custom_schema_name | trim }}{%- endif -%}
{%- endmacro %}
