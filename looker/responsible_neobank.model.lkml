# Responsible Neobank Growth — LookML model (Plan 3, Task 9).
# Semantic boundary per ADR-route-c-dbt-looker-boundary: dbt owns state,
# eligibility and reconciliation logic; LookML owns naming, additive measures,
# joins, drills and dashboards. Every Explore reads a governed
# presentation/logical relation from the parity-proven optimised lineage.
# Authored locally before trial activation; validated only once the trial's
# LookML/SQL/Assert/Content validators run.

connection: "route_c_bigquery"

include: "/views/*.view.lkml"
include: "/dashboards/*.dashboard.lookml"

# Cache follows real warehouse freshness, not arbitrary long caching.
datagroup: route_c_default {
  sql_trigger: SELECT MAX(run_date) FROM neobank_p3o_20260717_logical.lgl_warehouse_health ;;
  max_cache_age: "4 hours"
}
persist_with: route_c_default

# Where applicants progress or drop between application, approval and funded
# activation, by campaign/referral cohort and synthetic outcome guardrail.
explore: growth_acquisition {
  label: "Growth acquisition"
  description: "One row per customer application journey (synthetic benchmark data; no real customers)."
}

# Whether referral activity creates incremental activated customers at
# sustainable reward cost.
explore: referral_economics {
  label: "Referral economics"
  description: "One row per referral with Finance-owned booked reward cost (synthetic benchmark data)."
}

# Which expected referral rewards are missing, duplicated, mismatched, stale
# or incorrectly reversed.
explore: reward_reconciliation {
  label: "Reward reconciliation"
  description: "One row per qualified referral per reconciliation day (synthetic subledger; illustrative accounting treatment)."
}

# Which models/interfaces are stale, failing, expensive or slower than their
# measured baseline.
explore: warehouse_health {
  label: "Warehouse health"
  description: "One row per governed interface per run day; cost fields only where a dated BigQuery measurement exists."
}
