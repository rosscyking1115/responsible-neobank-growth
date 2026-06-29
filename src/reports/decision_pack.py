"""Build and render the responsible-growth decision pack."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.inclusion import (
    abandonment_by_segment,
    assisted_onboarding_segments,
    funnel_conversion,
)
from src.protection import assess_events
from src.release_decisions import ReleaseDecision
from src.wellbeing.metrics import outcome_gap

FAIRNESS_SEGMENTS = ["digital_confidence_band", "income_band", "vulnerable_customer_proxy"]
FAIRNESS_OUTCOMES = ["activated_d7", "has_support_contact", "has_complaint"]
OUTCOME_LABELS = {
    "activated_d7": "D7 activation",
    "has_support_contact": "Support contact",
    "has_complaint": "Complaint",
}


@dataclass(frozen=True)
class BusinessImpactSummary:
    feature_name: str
    release_recommendation: str
    evidence_tier: str
    worst_fairness_gap_pp: float
    worst_fairness_label: str
    onboarding_completion_rate: float
    assisted_onboarding_customers: int
    worst_abandonment_segment: str
    worst_abandonment_rate: float
    fair_value_downgrades: int
    protection_intervention_rate: float
    protection_human_review: int
    impact_statements: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResponsibleGrowthReport:
    generated_at: str
    summary: BusinessImpactSummary
    release_decision: ReleaseDecision | None
    fairness_gaps: pd.DataFrame
    onboarding_funnel: pd.DataFrame
    onboarding_abandonment: pd.DataFrame
    fair_value: pd.DataFrame
    protection_summary: pd.DataFrame


def _fairness_gaps(customer_outcomes: pd.DataFrame) -> pd.DataFrame:
    columns = ["segment", "outcome", "gap_pp", "higher_rate_level", "lower_rate_level"]
    if customer_outcomes.empty:
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, object]] = []
    for segment in FAIRNESS_SEGMENTS:
        if segment not in customer_outcomes.columns:
            continue
        for outcome in FAIRNESS_OUTCOMES:
            if outcome not in customer_outcomes.columns:
                continue
            gap = outcome_gap(customer_outcomes, segment, outcome, min_segment_size=30)
            if gap is None:
                continue
            rows.append(
                {
                    "segment": segment,
                    "outcome": OUTCOME_LABELS.get(outcome, outcome),
                    "gap_pp": round(gap.gap * 100, 2),
                    "higher_rate_level": gap.best_level,
                    "lower_rate_level": gap.worst_level,
                }
            )
    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values("gap_pp", ascending=False)
        .reset_index(drop=True)
    )


def _protection_summary(protection_events: pd.DataFrame) -> pd.DataFrame:
    columns = ["action", "events", "share"]
    if protection_events.empty:
        return pd.DataFrame(columns=columns)
    assessed = assess_events(protection_events)
    total = len(assessed)
    counts = assessed["action"].value_counts()
    rows = [
        {"action": str(action), "events": int(events), "share": round(int(events) / total, 4)}
        for action, events in counts.items()
    ]
    return pd.DataFrame(rows, columns=columns).sort_values("events", ascending=False)


def _impact_statements(summary_fields: dict[str, object]) -> list[str]:
    statements = [
        f"Release recommendation: {summary_fields['release_recommendation']} "
        f"({summary_fields['evidence_tier']} evidence)."
    ]
    if summary_fields["worst_fairness_gap_pp"] > 0:
        gap_pp = summary_fields["worst_fairness_gap_pp"]
        label = summary_fields["worst_fairness_label"]
        statements.append(f"Largest customer-outcome disparity: {gap_pp:.1f}pp ({label}).")
    statements.append(
        f"Onboarding completion {summary_fields['onboarding_completion_rate']:.0%}; "
        f"{summary_fields['assisted_onboarding_customers']:,} customers flagged for "
        f"assisted onboarding."
    )
    if summary_fields["fair_value_downgrades"] > 0:
        statements.append(
            f"{summary_fields['fair_value_downgrades']} pricing offer(s) downgraded "
            f"from scale on fair-value grounds."
        )
    statements.append(
        f"{summary_fields['protection_intervention_rate']:.0%} of monitored transfers "
        f"triggered a supportive intervention; "
        f"{summary_fields['protection_human_review']:,} routed to human review."
    )
    return statements


def build_report(
    *,
    feature_name: str,
    release_decision: ReleaseDecision | None,
    customer_outcomes: pd.DataFrame,
    onboarding_funnel: pd.DataFrame,
    fair_value: pd.DataFrame,
    protection_events: pd.DataFrame,
    generated_at: datetime | None = None,
) -> ResponsibleGrowthReport:
    """Assemble the decision pack from engine outputs and raw mart frames."""

    fairness = _fairness_gaps(customer_outcomes)
    funnel = funnel_conversion(onboarding_funnel)
    abandonment = (
        abandonment_by_segment(onboarding_funnel, "digital_confidence_band")
        if not onboarding_funnel.empty
        else pd.DataFrame()
    )
    protection = _protection_summary(protection_events)

    completion = (
        float(onboarding_funnel["completed_onboarding"].astype(float).mean())
        if not onboarding_funnel.empty
        else 0.0
    )
    assisted = (
        int(onboarding_funnel["needs_assisted_onboarding"].astype(bool).sum())
        if "needs_assisted_onboarding" in onboarding_funnel.columns
        else 0
    )
    worst_abandon = ("n/a", 0.0)
    flags = (
        assisted_onboarding_segments(onboarding_funnel, "digital_confidence_band")
        if not onboarding_funnel.empty
        else []
    )
    if flags:
        worst = max(flags, key=lambda f: f.abandonment_rate)
        worst_abandon = (worst.level, worst.abandonment_rate)

    downgrades = (
        int(fair_value["downgraded"].astype(bool).sum())
        if not fair_value.empty and "downgraded" in fair_value.columns
        else 0
    )

    protection_total = int(protection["events"].sum()) if not protection.empty else 0
    no_action = (
        int(protection.loc[protection["action"] == "no_action", "events"].sum())
        if not protection.empty
        else 0
    )
    intervention_rate = (
        (protection_total - no_action) / protection_total if protection_total else 0.0
    )
    human_review = (
        int(protection.loc[protection["action"] == "human_review_recommendation", "events"].sum())
        if not protection.empty
        else 0
    )

    worst_gap = float(fairness["gap_pp"].iloc[0]) if not fairness.empty else 0.0
    worst_gap_label = (
        f"{fairness['outcome'].iloc[0]} across {fairness['segment'].iloc[0]}"
        if not fairness.empty
        else "n/a"
    )

    fields = {
        "feature_name": feature_name,
        "release_recommendation": release_decision.decision if release_decision else "n/a",
        "evidence_tier": release_decision.evidence_tier if release_decision else "n/a",
        "worst_fairness_gap_pp": worst_gap,
        "worst_fairness_label": worst_gap_label,
        "onboarding_completion_rate": completion,
        "assisted_onboarding_customers": assisted,
        "worst_abandonment_segment": worst_abandon[0],
        "worst_abandonment_rate": worst_abandon[1],
        "fair_value_downgrades": downgrades,
        "protection_intervention_rate": intervention_rate,
        "protection_human_review": human_review,
    }
    summary = BusinessImpactSummary(**fields, impact_statements=_impact_statements(fields))

    return ResponsibleGrowthReport(
        generated_at=(generated_at or datetime.now(UTC)).isoformat(timespec="seconds"),
        summary=summary,
        release_decision=release_decision,
        fairness_gaps=fairness,
        onboarding_funnel=funnel,
        onboarding_abandonment=abandonment,
        fair_value=fair_value,
        protection_summary=protection,
    )


# --- rendering --------------------------------------------------------------


def _md_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    header = "| " + " | ".join(str(c) for c in frame.columns) + " |"
    divider = "| " + " | ".join("---" for _ in frame.columns) + " |"
    rows = [
        "| " + " | ".join(str(v) for v in record) + " |"
        for record in frame.itertuples(index=False)
    ]
    return "\n".join([header, divider, *rows])


def render_markdown(report: ResponsibleGrowthReport) -> str:
    s = report.summary
    return f"""# Responsible Growth Decision Pack

- Generated at: `{report.generated_at}`
- Feature: `{s.feature_name}`
- Release recommendation: **{s.release_recommendation.upper()}** ({s.evidence_tier} evidence)

## Business impact summary

{chr(10).join(f"- {line}" for line in s.impact_statements)}

## Customer-outcome fairness gaps

{_md_table(report.fairness_gaps)}

## Onboarding funnel

{_md_table(report.onboarding_funnel)}

## Onboarding abandonment by digital confidence

{_md_table(report.onboarding_abandonment)}

## Fair-value pricing governance

{_md_table(report.fair_value)}

## Customer-protection interventions

{_md_table(report.protection_summary)}

---

_Synthetic data. Wellbeing, inclusion, and protection fields are simulated proxies for
evaluating product decisions and must not be used for punitive, credit, or
service-denial decisions._
"""


def _html_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "<p><em>No rows.</em></p>"
    return frame.to_html(index=False, border=0, classes="pack-table")


def render_html(report: ResponsibleGrowthReport) -> str:
    s = report.summary
    impact = "".join(f"<li>{line}</li>" for line in s.impact_statements)
    decision_color = {
        "ship": "#00A88F",
        "limited_rollout": "#0B66C3",
        "experiment_only": "#F2B544",
        "needs_human_review": "#7C6FE8",
        "block": "#EF4444",
        "n/a": "#6B7280",
    }.get(s.release_recommendation, "#0B66C3")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Responsible Growth Decision Pack</title>
<style>
  body {{ font-family: Inter, "Segoe UI", system-ui, sans-serif; color: #202436;
         max-width: 920px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
  h1 {{ margin-bottom: 0.2rem; }}
  .meta {{ color: #5f6b85; font-size: 0.9rem; }}
  .verdict {{ display: inline-block; margin: 0.8rem 0; padding: 0.5rem 1rem;
              border-radius: 6px; color: #fff; font-weight: 700; font-size: 1.2rem;
              background: {decision_color}; }}
  h2 {{ margin-top: 1.8rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3rem; }}
  table.pack-table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
  table.pack-table th, table.pack-table td {{ text-align: left; padding: 0.4rem 0.6rem;
              border-bottom: 1px solid #eef0f4; }}
  table.pack-table th {{ background: #f8fafc; }}
  .disclaimer {{ color: #5f6b85; font-size: 0.85rem; margin-top: 2rem; }}
</style></head><body>
<h1>Responsible Growth Decision Pack</h1>
<p class="meta">Generated {report.generated_at} &middot; Feature: <code>{s.feature_name}</code></p>
<div class="verdict">{s.release_recommendation.upper()}</div>
<p class="meta">{s.evidence_tier} evidence</p>
<h2>Business impact summary</h2>
<ul>{impact}</ul>
<h2>Customer-outcome fairness gaps</h2>
{_html_table(report.fairness_gaps)}
<h2>Onboarding funnel</h2>
{_html_table(report.onboarding_funnel)}
<h2>Onboarding abandonment by digital confidence</h2>
{_html_table(report.onboarding_abandonment)}
<h2>Fair-value pricing governance</h2>
{_html_table(report.fair_value)}
<h2>Customer-protection interventions</h2>
{_html_table(report.protection_summary)}
<p class="disclaimer">Synthetic data. Wellbeing, inclusion, and protection fields are
simulated proxies for evaluating product decisions and must not be used for punitive,
credit, or service-denial decisions.</p>
</body></html>
"""


def _summary_frame(summary: BusinessImpactSummary) -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("Feature", summary.feature_name),
            ("Release recommendation", summary.release_recommendation),
            ("Evidence tier", summary.evidence_tier),
            ("Worst fairness gap (pp)", summary.worst_fairness_gap_pp),
            ("Worst fairness gap", summary.worst_fairness_label),
            ("Onboarding completion rate", round(summary.onboarding_completion_rate, 4)),
            ("Assisted-onboarding customers", summary.assisted_onboarding_customers),
            ("Worst abandonment segment", summary.worst_abandonment_segment),
            ("Worst abandonment rate", round(summary.worst_abandonment_rate, 4)),
            ("Fair-value downgrades", summary.fair_value_downgrades),
            ("Protection intervention rate", round(summary.protection_intervention_rate, 4)),
            ("Protection human reviews", summary.protection_human_review),
        ],
        columns=["metric", "value"],
    )


def _write_sheets(report: ResponsibleGrowthReport, writer: pd.ExcelWriter) -> None:
    _summary_frame(report.summary).to_excel(writer, sheet_name="Summary", index=False)
    pd.DataFrame({"impact_statement": report.summary.impact_statements}).to_excel(
        writer, sheet_name="Impact", index=False
    )
    report.fairness_gaps.to_excel(writer, sheet_name="Fairness gaps", index=False)
    report.onboarding_funnel.to_excel(writer, sheet_name="Onboarding funnel", index=False)
    report.onboarding_abandonment.to_excel(writer, sheet_name="Abandonment", index=False)
    report.fair_value.to_excel(writer, sheet_name="Fair-value pricing", index=False)
    report.protection_summary.to_excel(writer, sheet_name="Protection", index=False)


def write_excel(report: ResponsibleGrowthReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        _write_sheets(report, writer)
    return path


def report_excel_bytes(report: ResponsibleGrowthReport) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        _write_sheets(report, writer)
    return buffer.getvalue()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build the responsible-growth decision pack.")
    parser.add_argument("--db", type=Path, default=Path("neobank.duckdb"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/reports"))
    parser.add_argument("--feature", default="personalised_onboarding_pot_prompt")
    args = parser.parse_args()

    # Lazy import: the dashboard layer owns data loading and cross-engine assembly.
    from app.dashboard_data import (
        load_dashboard_data,
        offer_fair_value,
        onboarding_release_decision,
    )

    data = load_dashboard_data(args.db)
    report = build_report(
        feature_name=args.feature,
        release_decision=onboarding_release_decision(
            data.experiment_variants, data.customer_outcomes
        ),
        customer_outcomes=data.customer_outcomes,
        onboarding_funnel=data.onboarding_funnel,
        fair_value=offer_fair_value(data.pricing_recommendations),
        protection_events=data.protection_events,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "responsible_growth_report.md").write_text(
        render_markdown(report), encoding="utf-8"
    )
    (args.output_dir / "responsible_growth_report.html").write_text(
        render_html(report), encoding="utf-8"
    )
    write_excel(report, args.output_dir / "responsible_growth_report.xlsx")
    print(f"Wrote decision pack to {args.output_dir.resolve()}")
    for line in report.summary.impact_statements:
        print(f"- {line}")


if __name__ == "__main__":
    main()
