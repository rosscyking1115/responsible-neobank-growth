# Reward Reconciliation dashboard (Plan 3 section 13.2).
- dashboard: reward_reconciliation
  title: "Reward Reconciliation"
  layout: newspaper
  description: "Synthetic referral-reward subledger with an illustrative double-entry treatment — not any real bank's accounting policy."

  filters:
    - name: reconciliation_window
      title: "Reconciliation month"
      type: field_filter
      model: responsible_neobank
      explore: reward_reconciliation
      field: reward_reconciliation.reconciliation_month

  elements:
    - name: expected_vs_actual
      title: "Expected vs booked / settled / reversed (£, minor units in dbt)"
      model: responsible_neobank
      explore: reward_reconciliation
      type: looker_line
      fields: [reward_reconciliation.reconciliation_date,
               reward_reconciliation.expected_amount_gbp,
               reward_reconciliation.booked_amount_gbp,
               reward_reconciliation.settled_amount_gbp,
               reward_reconciliation.reversed_amount_gbp]
      listen:
        reconciliation_window: reward_reconciliation.reconciliation_month

    - name: outstanding_payable
      title: "Outstanding payable by day (booked − settled − reversed)"
      model: responsible_neobank
      explore: reward_reconciliation
      type: looker_area
      fields: [reward_reconciliation.reconciliation_date,
               reward_reconciliation.outstanding_payable_gbp]
      listen:
        reconciliation_window: reward_reconciliation.reconciliation_month

    - name: exceptions_by_reason
      title: "Open exceptions by reason and age"
      model: responsible_neobank
      explore: reward_reconciliation
      type: looker_grid
      fields: [reward_reconciliation.exception_reason,
               reward_reconciliation.exception_count,
               reward_reconciliation.exception_age_days]
      filters:
        reward_reconciliation.exception_reason: "-NULL"
      sorts: [reward_reconciliation.exception_count desc]
      listen:
        reconciliation_window: reward_reconciliation.reconciliation_month

    - name: exception_drill
      title: "Exception drill: referral → event trace (fictional identifiers)"
      model: responsible_neobank
      explore: reward_reconciliation
      type: looker_grid
      fields: [reward_reconciliation.referral_id, reward_reconciliation.reward_id,
               reward_reconciliation.reconciliation_date,
               reward_reconciliation.exception_reason,
               reward_reconciliation.lifecycle_status]
      filters:
        reward_reconciliation.exception_reason: "-NULL"
      limit: 50
      listen:
        reconciliation_window: reward_reconciliation.reconciliation_month

    - name: balance_check
      title: "Unbalanced rows (must be zero)"
      model: responsible_neobank
      explore: reward_reconciliation
      type: single_value
      fields: [reward_reconciliation.unbalanced_rows]
