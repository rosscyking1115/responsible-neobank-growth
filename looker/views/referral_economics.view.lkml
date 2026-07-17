view: referral_economics {
  sql_table_name: neobank_p3o_20260717_presentation.prs_referral_economics ;;

  # --- dimensions -----------------------------------------------------------

  dimension: referral_id {
    primary_key: yes
    type: string
    description: "Fictional referral identifier (one row per referral)."
    sql: ${TABLE}.referral_id ;;
  }

  dimension: invite_channel {
    type: string
    sql: ${TABLE}.invite_channel ;;
  }

  dimension_group: invited {
    type: time
    timeframes: [date, week, month]
    convert_tz: no
    sql: ${TABLE}.invited_at ;;
  }

  dimension: invite_cohort_month {
    type: date_month
    convert_tz: no
    description: "Referral cohort by invitation month."
    sql: ${TABLE}.invite_cohort_month ;;
  }

  dimension: is_qualified { type: yesno sql: ${TABLE}.is_qualified ;; }

  dimension: referred_customer_funded {
    type: yesno
    description: "Whether the referred customer reached funded activation."
    sql: ${TABLE}.referred_customer_funded ;;
  }

  dimension: lifecycle_status {
    type: string
    description: "invited / qualified / booked / settled / reversed."
    sql: ${TABLE}.lifecycle_status ;;
  }

  dimension: exception_reason {
    type: string
    description: "Reconciliation exception reason code (append-only set), if any."
    sql: ${TABLE}.exception_reason ;;
  }

  dimension: booked_minor { type: number hidden: yes sql: ${TABLE}.booked_minor ;; }

  # --- measures -------------------------------------------------------------

  measure: invitations { type: count }

  measure: qualifications {
    type: count
    filters: [is_qualified: "yes"]
    description: "Canonically qualified referrals (qualification rules live in dbt)."
  }

  measure: funded_referred_customers {
    type: count
    filters: [referred_customer_funded: "yes"]
  }

  measure: reward_booked_cost_gbp {
    type: sum
    value_format_name: gbp
    description: "Finance-owned booked reward cost; stored in integer minor units, converted for display only."
    sql: ${TABLE}.booked_minor / 100.0 ;;
  }

  measure: reward_settled_gbp {
    type: sum
    value_format_name: gbp
    sql: ${TABLE}.settled_minor / 100.0 ;;
  }

  measure: cost_per_funded_referred_gbp {
    type: number
    value_format_name: gbp
    description: "Booked reward cost / funded referred customers (governed numerator and denominator; no average-of-averages)."
    sql: ${reward_booked_cost_gbp} / nullif(${funded_referred_customers}, 0) ;;
  }

  # Incrementality estimates come only from governed dbt outputs; the columns
  # are null until the governed estimate lands (never recomputed in LookML).
  measure: incremental_activated_estimate {
    type: average
    description: "Experiment-based incremental activation estimate from governed dbt outputs (null in this release)."
    sql: ${TABLE}.incremental_activated_estimate ;;
  }
}
