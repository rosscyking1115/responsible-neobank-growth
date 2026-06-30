"""Adapters that run the platform's analysis on real public datasets."""

from src.adapters.uci_bank_marketing import (
    SEGMENTS,
    conversion_summary,
    fairness_gaps,
    load_bank_marketing,
    prepare,
    render_markdown,
)

__all__ = [
    "SEGMENTS",
    "conversion_summary",
    "fairness_gaps",
    "load_bank_marketing",
    "prepare",
    "render_markdown",
]
