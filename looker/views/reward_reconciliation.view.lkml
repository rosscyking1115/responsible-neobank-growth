view: reward_reconciliation {
  sql_table_name: neobank_p3o_20260717_logical.lgl_reward_ledger_reconciliation ;;

  # Composite grain: one row per qualified referral per reconciliation day.
  # (The Plan 1 field inventory named reward_id as part of the key; the
  # implemented table keys on referral_id because a missing posting has no
  # reward_id yet — deviation recorded in looker/README.md.)

  dimension: reconciliation_key {
    primary_key: yes
    hidden: yes
    type: string
    sql: concat(${TABLE}.referral_id, '|', cast(${TABLE}.reconciliation_date as string)) ;;
  }

  dimension: referral_id {
    type: string
    description: "Fictional referral identifier (drill path to the event trace)."
    sql: ${TABLE}.referral_id ;;
  }

  dimension: reward_id {
    type: string
    description: "Reward identifier; null while the posting is missing."
    sql: ${TABLE}.reward_id ;;
  }

  dimension_group: reconciliation {
    type: time
    timeframes: [date, week, month]
    convert_tz: no
    datatype: date
    sql: ${TABLE}.reconciliation_date ;;
  }

  dimension: lifecycle_status {
    type: string
    sql: ${TABLE}.lifecycle_status ;;
  }

  dimension: exception_reason {
    type: string
    description: "missing_posting / duplicate_posting / amount_mismatch / settlement_without_booking / reversal_beyond_booked_amount / unbalanced_journal / pending_beyond_synthetic_sla."
    sql: ${TABLE}.exception_reason ;;
  }

  dimension: exception_age_days {
    type: number
    sql: ${TABLE}.exception_age_days ;;
  }

  dimension: is_balanced { type: yesno sql: ${TABLE}.is_balanced ;; }

  # --- measures (integer minor units; converted for display only) ----------

  measure: entitlements { type: count }

  measure: expected_amount_gbp {
    type: sum
    value_format_name: gbp
    sql: ${TABLE}.entitled_minor / 100.0 ;;
  }

  measure: booked_amount_gbp {
    type: sum
    value_format_name: gbp
    sql: ${TABLE}.booked_minor / 100.0 ;;
  }

  measure: settled_amount_gbp {
    type: sum
    value_format_name: gbp
    sql: ${TABLE}.settled_minor / 100.0 ;;
  }

  measure: reversed_amount_gbp {
    type: sum
    value_format_name: gbp
    sql: ${TABLE}.reversed_minor / 100.0 ;;
  }

  measure: outstanding_payable_gbp {
    type: sum
    value_format_name: gbp
    description: "Booked − settled − reversed; balance rules live in dbt, never re-derived here."
    sql: ${TABLE}.outstanding_payable_minor / 100.0 ;;
  }

  measure: exception_count {
    type: count
    filters: [exception_reason: "-NULL"]
    description: "Open reconciliation exceptions (reason logic lives in dbt)."
  }

  measure: unbalanced_rows {
    type: count
    filters: [is_balanced: "no"]
  }
}
