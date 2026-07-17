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

{% macro ts_sub_days(expression, days) -%}
    {%- if target.type == 'bigquery' -%}
        timestamp_sub({{ expression }}, interval {{ days }} day)
    {%- else -%}
        ({{ expression }} - interval {{ days }} day)
    {%- endif -%}
{%- endmacro %}

{#
  Incremental selection contract (docs/contracts/incremental-correctness.md):
  select rows whose ingestion falls after the processed watermark minus the
  frozen lookback. Rows arriving with an ingestion time older than
  watermark - lookback are deliberately skipped by ordinary runs and require
  an explicit bounded backfill (vars backfill_start/backfill_end, exclusive
  end), executed via tools/reconcile/backfill.py so reason and operator are
  recorded.
#}
{% macro incremental_ingestion_filter(ts_column='ingested_at') %}
    {%- if is_incremental() %}
    and (
        {{ ts_column }} > {{ ts_sub_days(
            '(select coalesce(max(' ~ ts_column ~ "), cast('1900-01-01' as timestamp)) from "
            ~ this ~ ')',
            var('lookback_days', 3)
        ) }}
        {%- if var('backfill_start', '') and var('backfill_end', '') %}
        or (
            {{ ts_column }} >= cast('{{ var("backfill_start") }}' as timestamp)
            and {{ ts_column }} < cast('{{ var("backfill_end") }}' as timestamp)
        )
        {%- endif %}
    )
    {%- endif %}
{% endmacro %}

{% macro ts_add_days(expression, days) -%}
    {%- if target.type == 'bigquery' -%}
        timestamp_add({{ expression }}, interval {{ days }} day)
    {%- else -%}
        ({{ expression }} + interval {{ days }} day)
    {%- endif -%}
{%- endmacro %}

{% macro date_diff_days(later, earlier) -%}
    {%- if target.type == 'bigquery' -%}
        date_diff({{ later }}, {{ earlier }}, day)
    {%- else -%}
        ({{ later }} - {{ earlier }})
    {%- endif -%}
{%- endmacro %}

{% macro json_value(column, key) -%}
    {%- if target.type == 'bigquery' -%}
        json_value({{ column }}, '$.{{ key }}')
    {%- else -%}
        json_extract_string({{ column }}, '$.{{ key }}')
    {%- endif -%}
{%- endmacro %}
