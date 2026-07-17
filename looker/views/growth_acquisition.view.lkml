view: growth_acquisition {
  sql_table_name: neobank_p3o_20260717_presentation.prs_growth_acquisition ;;

  # --- dimensions -----------------------------------------------------------

  dimension: application_id {
    primary_key: yes
    type: string
    description: "Fictional application identifier (one row per customer application journey)."
    sql: ${TABLE}.application_id ;;
  }

  dimension: customer_id {
    type: string
    hidden: yes
    sql: ${TABLE}.customer_id ;;
  }

  dimension_group: application {
    type: time
    timeframes: [date, week, month]
    convert_tz: no
    datatype: date
    description: "Application submission business date (UTC)."
    sql: ${TABLE}.application_date ;;
  }

  dimension: channel {
    type: string
    description: "Acquisition channel (organic / paid / referral / partnership)."
    sql: ${TABLE}.channel ;;
  }

  dimension: campaign_id {
    type: string
    sql: ${TABLE}.campaign_id ;;
  }

  dimension: is_referred {
    type: yesno
    sql: ${TABLE}.is_referred ;;
  }

  dimension: experiment_variant {
    type: string
    description: "Experiment arm where a valid assignment exists (control / treatment)."
    sql: ${TABLE}.experiment_variant ;;
  }

  dimension: journey_stage {
    type: string
    description: "applied / rejected / manual_review / approved / activated / funded."
    sql: ${TABLE}.journey_stage ;;
  }

  dimension: customer_outcome_flag {
    type: yesno
    description: "SYNTHETIC customer-outcome guardrail signal — illustrative only, never evidence about real customers."
    sql: ${TABLE}.customer_outcome_flag ;;
  }

  dimension: is_approved { type: yesno hidden: yes sql: ${TABLE}.is_approved ;; }
  dimension: is_activated { type: yesno hidden: yes sql: ${TABLE}.is_activated ;; }
  dimension: is_funded { type: yesno hidden: yes sql: ${TABLE}.is_funded ;; }

  # --- measures (additive, over the governed grain only) --------------------

  measure: applications {
    type: count
    description: "Count of submitted applications."
  }

  measure: approved_accounts {
    type: count
    filters: [is_approved: "yes"]
    description: "Applications whose canonical KYC decision is approved."
  }

  measure: activated_accounts {
    type: count
    filters: [is_activated: "yes"]
    description: "Approved applications with a canonical activation."
  }

  measure: funded_activations {
    type: count
    filters: [is_funded: "yes"]
    description: "Activated accounts with a canonical first funding."
  }

  measure: activation_rate {
    type: number
    value_format_name: percent_1
    description: "Funded activations / applications (denominator: all applications)."
    sql: 1.0 * ${funded_activations} / nullif(${applications}, 0) ;;
  }

  measure: outcome_flag_rate {
    type: number
    value_format_name: percent_1
    description: "SYNTHETIC guardrail: share of journeys with an outcome signal; illustrative only."
    sql: 1.0 * count(case when ${TABLE}.customer_outcome_flag then 1 end)
         / nullif(${applications}, 0) ;;
  }
}
