"""Adapters that run the platform's analysis on real public datasets."""

from src.adapters.criteo_uplift import (
    CriteoReadout,
    experiment_readout,
    load_criteo,
)
from src.adapters.criteo_uplift import (
    prepare as prepare_criteo,
)
from src.adapters.criteo_uplift import (
    render_markdown as render_criteo_markdown,
)
from src.adapters.uci_bank_marketing import (
    SEGMENTS,
    conversion_summary,
    fairness_gaps,
    fetch_bank_marketing,
    load_bank_marketing,
    prepare,
    render_markdown,
)

__all__ = [
    # UCI Bank Marketing (fairness cross-check)
    "SEGMENTS",
    "conversion_summary",
    "fairness_gaps",
    "fetch_bank_marketing",
    "load_bank_marketing",
    "prepare",
    "render_markdown",
    # Criteo Uplift (experiment cross-check)
    "CriteoReadout",
    "experiment_readout",
    "load_criteo",
    "prepare_criteo",
    "render_criteo_markdown",
]
