# Responsible Growth Decision dashboard (Plan 3 section 13.1).
# Every tile traces to a governed Explore; denominators, cohorts and the
# synthetic-data boundary are visible on the dashboard itself.
- dashboard: responsible_growth
  title: "Responsible Growth Decision"
  layout: newspaper
  description: "Synthetic benchmark data — no real customers, no affiliation with any real bank. Denominators are labelled per tile."

  filters:
    - name: application_window
      title: "Application month"
      type: field_filter
      model: responsible_neobank
      explore: growth_acquisition
      field: growth_acquisition.application_month

  elements:
    - name: funnel_overview
      title: "Application → funded activation funnel (denominator: all applications)"
      model: responsible_neobank
      explore: growth_acquisition
      type: looker_column
      fields: [growth_acquisition.applications, growth_acquisition.approved_accounts,
               growth_acquisition.activated_accounts, growth_acquisition.funded_activations]
      listen:
        application_window: growth_acquisition.application_month

    - name: activation_by_channel
      title: "Activation rate by channel (funded / applications)"
      model: responsible_neobank
      explore: growth_acquisition
      type: looker_bar
      fields: [growth_acquisition.channel, growth_acquisition.activation_rate,
               growth_acquisition.applications]
      sorts: [growth_acquisition.activation_rate desc]
      listen:
        application_window: growth_acquisition.application_month

    - name: experiment_arms
      title: "Funded activation by experiment arm (assignment stability enforced in dbt)"
      model: responsible_neobank
      explore: growth_acquisition
      type: looker_column
      fields: [growth_acquisition.experiment_variant, growth_acquisition.funded_activations,
               growth_acquisition.applications]
      filters:
        growth_acquisition.experiment_variant: "-NULL"
      listen:
        application_window: growth_acquisition.application_month

    - name: referral_cost
      title: "Referral reward cost vs funded referred customers"
      model: responsible_neobank
      explore: referral_economics
      type: looker_line
      fields: [referral_economics.invite_cohort_month, referral_economics.reward_booked_cost_gbp,
               referral_economics.funded_referred_customers]

    - name: outcome_guardrail
      title: "SYNTHETIC customer-outcome guardrail rate (illustrative only)"
      model: responsible_neobank
      explore: growth_acquisition
      type: single_value
      fields: [growth_acquisition.outcome_flag_rate]
      listen:
        application_window: growth_acquisition.application_month

    - name: freshness_footer
      title: "Interface freshness (from warehouse_health)"
      model: responsible_neobank
      explore: warehouse_health
      type: looker_grid
      fields: [warehouse_health.model_name, warehouse_health.freshness_status,
               warehouse_health.run_date]
      sorts: [warehouse_health.run_date desc]
      limit: 6
