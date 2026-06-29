# Responsible Growth Decision Pack

The decision pack is the platform's **stakeholder-facing deliverable**: a single
report that pulls the outputs of every decision engine into one place, leads with a
plain-English **business-impact summary**, and exports to Markdown, self-contained
HTML (print-to-PDF ready), or a multi-sheet Excel workbook.

It answers, on one page: *should we ship, and at what cost to customers?*

## Where it lives

| Concern | Location |
| --- | --- |
| Report builder + renderers | [`src/reports/decision_pack.py`](../src/reports/decision_pack.py) |
| Dashboard download | "Responsible growth decision pack" expander on the Customer outcomes tab |
| Tests | [`tests/test_responsible_growth_report.py`](../tests/test_responsible_growth_report.py) |

## What it consolidates

- **Release recommendation** from the release-gate engine (`ship` / `limited_rollout`
  / `experiment_only` / `needs_human_review` / `block`) with its evidence tier.
- **Customer-outcome fairness gaps** — the largest activation / support / complaint
  disparities across wellbeing and inclusion segments.
- **Digital inclusion** — onboarding funnel conversion and abandonment by digital
  confidence, plus assisted-onboarding candidates.
- **Fair-value pricing governance** — per-offer fair-value scores and any offers
  downgraded from "scale".
- **Customer protection** — the distribution of supportive interventions.

## Business-impact summary

The headline is a short list of quantified statements, e.g.:

```text
- Release recommendation: limited_rollout (ship evidence).
- Largest customer-outcome disparity: 8.2pp (D7 activation across income_band).
- Onboarding completion 81%; 120 customers flagged for assisted onboarding.
- 41% of monitored transfers triggered a supportive intervention; 39 routed to human review.
```

## Generate it

From the live dashboard: **Customer outcomes → Responsible growth decision pack →
Download HTML / Download Excel**.

From the command line:

```powershell
uv run python -m src.reports.decision_pack --db neobank.duckdb --output-dir artifacts/reports
```

This writes `responsible_growth_report.{md,html,xlsx}`. The HTML is self-contained and
prints cleanly to PDF; the Excel workbook has one sheet per section (Summary, Impact,
Fairness gaps, Onboarding funnel, Abandonment, Fair-value pricing, Protection).
