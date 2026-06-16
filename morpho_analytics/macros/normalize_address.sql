{% macro normalize_address(column_name) %}
    lower(nullif(trim({{ column_name }}::text), ''))
{% endmacro %}
