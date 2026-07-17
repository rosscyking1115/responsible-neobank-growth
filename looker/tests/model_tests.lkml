# Assert tests (run by the trial's Assert validator; expected values come from
# the tiny/standard truth manifests — see docs/looker/evidence-checklist.md).

test: growth_acquisition_grain_is_unique {
  explore_source: growth_acquisition {
    column: application_id { field: growth_acquisition.application_id }
    column: applications { field: growth_acquisition.applications }
    sorts: [growth_acquisition.applications: desc]
    limit: 1
  }
  assert: one_row_per_application {
    expression: ${growth_acquisition.applications} = 1 ;;
  }
}

test: activation_rate_is_a_probability {
  explore_source: growth_acquisition {
    column: activation_rate { field: growth_acquisition.activation_rate }
  }
  assert: rate_between_zero_and_one {
    expression: ${growth_acquisition.activation_rate} >= 0 AND ${growth_acquisition.activation_rate} <= 1 ;;
  }
}

test: reconciliation_balances {
  explore_source: reward_reconciliation {
    column: unbalanced_rows { field: reward_reconciliation.unbalanced_rows }
  }
  assert: no_unbalanced_rows {
    expression: ${reward_reconciliation.unbalanced_rows} = 0 ;;
  }
}

test: referral_costs_are_non_negative {
  explore_source: referral_economics {
    column: reward_booked_cost_gbp { field: referral_economics.reward_booked_cost_gbp }
  }
  assert: booked_cost_non_negative {
    expression: ${referral_economics.reward_booked_cost_gbp} >= 0 ;;
  }
}
