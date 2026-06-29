"""Responsible-growth decision pack.

Assembles the outputs of the decision engines (release gate, fairness gaps, digital
inclusion, fair-value pricing, customer protection) into one stakeholder-facing
report with a business-impact summary, exportable as Markdown, HTML, or Excel.
"""

from src.reports.decision_pack import (
    BusinessImpactSummary,
    ResponsibleGrowthReport,
    build_report,
    render_html,
    render_markdown,
    report_excel_bytes,
    write_excel,
)

__all__ = [
    "BusinessImpactSummary",
    "ResponsibleGrowthReport",
    "build_report",
    "render_html",
    "render_markdown",
    "report_excel_bytes",
    "write_excel",
]
