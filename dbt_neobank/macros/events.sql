{% macro event_deliveries_table() -%}
    {%- if target.type == 'bigquery' -%}
        {{ source('neobank_events', 'raw_event_deliveries') }}
    {%- else -%}
        read_parquet('{{ var("events_warehouse", "data/warehouse") }}/raw_events/*.parquet')
    {%- endif -%}
{%- endmacro %}

{% macro event_quarantine_table() -%}
    {%- if target.type == 'bigquery' -%}
        {{ source('neobank_events', 'raw_event_quarantine') }}
    {%- else -%}
        read_parquet('{{ var("events_warehouse", "data/warehouse") }}/quarantine/*.parquet')
    {%- endif -%}
{%- endmacro %}

{% macro json_value(column, key) -%}
    {%- if target.type == 'bigquery' -%}
        json_value({{ column }}, '$.{{ key }}')
    {%- else -%}
        json_extract_string({{ column }}, '$.{{ key }}')
    {%- endif -%}
{%- endmacro %}
