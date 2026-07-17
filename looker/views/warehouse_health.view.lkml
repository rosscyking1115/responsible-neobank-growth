view: warehouse_health {
  sql_table_name: neobank_p3o_20260717_presentation.prs_warehouse_health_daily ;;

  dimension: health_key {
    primary_key: yes
    hidden: yes
    type: string
    sql: concat(${TABLE}.model_name, '|', cast(${TABLE}.run_date as string)) ;;
  }

  dimension: model_name {
    type: string
    description: "Governed interface (growth_acquisition / referral_economics / reward_reconciliation)."
    sql: ${TABLE}.model_name ;;
  }

  dimension_group: run {
    type: time
    timeframes: [date, week, month]
    convert_tz: no
    datatype: date
    sql: ${TABLE}.run_date ;;
  }

  dimension: owner { type: string sql: ${TABLE}.owner ;; }

  dimension: freshness_status {
    type: string
    description: "fresh / warn / error against the declared interface SLOs."
    sql: ${TABLE}.freshness_status ;;
  }

  dimension: strategy {
    type: string
    description: "full / incremental benchmark strategy label (null outside measured runs)."
    sql: ${TABLE}.strategy ;;
  }

  # --- measures -------------------------------------------------------------

  measure: interface_days { type: count }

  measure: deliveries_ingested {
    type: sum
    sql: ${TABLE}.deliveries_ingested ;;
  }

  measure: deliveries_quarantined {
    type: sum
    sql: ${TABLE}.deliveries_quarantined ;;
  }

  measure: stale_interface_days {
    type: count
    filters: [freshness_status: "warn,error"]
  }

  measure: bytes_processed {
    type: sum
    description: "BigQuery bytes processed — populated only where a dated Plan 3 measurement exists; null is 'not measured', never zero cost."
    sql: ${TABLE}.bytes_processed ;;
  }

  measure: estimated_cost {
    type: sum
    description: "Estimated on-demand cost with recorded pricing date; null means not measured."
    sql: ${TABLE}.estimated_cost ;;
  }
}
