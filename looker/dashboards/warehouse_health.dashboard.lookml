# Warehouse Health and Cost dashboard (Plan 3 section 13.3).
# Portfolio observability over the synthetic benchmark — not evidence of
# running any real bank's warehouse.
- dashboard: warehouse_health
  title: "Warehouse Health and Cost"
  layout: newspaper
  description: "Freshness, quality and measured benchmark evidence for the governed interfaces. Cost fields appear only where a dated BigQuery measurement exists (null = not measured, never zero)."

  elements:
    - name: freshness_grid
      title: "Freshness status by interface and day"
      model: responsible_neobank
      explore: warehouse_health
      type: looker_grid
      fields: [warehouse_health.model_name, warehouse_health.run_date,
               warehouse_health.freshness_status,
               warehouse_health.deliveries_ingested,
               warehouse_health.deliveries_quarantined]
      sorts: [warehouse_health.run_date desc]
      limit: 30

    - name: stale_days
      title: "Interface-days breaching freshness SLO"
      model: responsible_neobank
      explore: warehouse_health
      type: single_value
      fields: [warehouse_health.stale_interface_days]

    - name: quarantine_trend
      title: "Quarantined deliveries over time (quarantine is evidence, not dropping)"
      model: responsible_neobank
      explore: warehouse_health
      type: looker_line
      fields: [warehouse_health.run_date, warehouse_health.deliveries_quarantined]

    - name: benchmark_note
      title: "Benchmark evidence"
      type: text
      body_text: |
        Full-versus-incremental measurements for this warehouse live in the
        repository (artifacts/plan3/benchmark-summary.json): on the
        569k-delivery benchmark, incremental processing billed +1.95% more
        bytes than a full rebuild on unpartitioned raw storage while using
        62.7% less compute (median slot-ms); the same 7-day reconciliation
        query processed 523.9x fewer bytes on partitioned storage. Absolute
        values and formulas are recorded with the pricing date; results are
        not extrapolated beyond this benchmark.
