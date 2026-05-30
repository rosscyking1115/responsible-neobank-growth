{% macro raw_table(table_name, file_name) -%}
    {%- if target.type == 'bigquery' -%}
        {{ source('neobank_raw', table_name) }}
    {%- else -%}
        read_parquet('{{ var("raw_path", "raw/ci") }}/{{ file_name }}')
    {%- endif -%}
{%- endmacro %}

{% macro integer_type() -%}
    {%- if target.type == 'bigquery' -%}
        int64
    {%- else -%}
        integer
    {%- endif -%}
{%- endmacro %}

{% macro float_type() -%}
    {%- if target.type == 'bigquery' -%}
        float64
    {%- else -%}
        double
    {%- endif -%}
{%- endmacro %}

{% macro date_trunc_day(part, expression) -%}
    {%- if target.type == 'bigquery' -%}
        {%- if part == 'week' -%}
            date_trunc({{ expression }}, week(monday))
        {%- else -%}
            date_trunc({{ expression }}, {{ part | upper }})
        {%- endif -%}
    {%- else -%}
        date_trunc('{{ part }}', {{ expression }})::date
    {%- endif -%}
{%- endmacro %}

{% macro date_diff_day(part, start_expression, end_expression) -%}
    {%- if target.type == 'bigquery' -%}
        {%- if part == 'week' -%}
            date_diff({{ end_expression }}, {{ start_expression }}, week(monday))
        {%- else -%}
            date_diff({{ end_expression }}, {{ start_expression }}, {{ part | upper }})
        {%- endif -%}
    {%- else -%}
        date_diff('{{ part }}', {{ start_expression }}, {{ end_expression }})
    {%- endif -%}
{%- endmacro %}

{% macro timestamp_add_days(expression, days) -%}
    {%- if target.type == 'bigquery' -%}
        timestamp_add({{ expression }}, interval {{ days }} day)
    {%- else -%}
        {{ expression }} + interval {{ days }} day
    {%- endif -%}
{%- endmacro %}
