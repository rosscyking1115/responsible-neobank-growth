"""Public benchmark anchors for calibrating the synthetic population.

The ``target`` values below are taken from named UK public sources (see ``source`` /
``url`` and docs/REAL_DATA_PROVENANCE.md). They anchor the synthetic distributions to
reality. They remain *point-in-time* figures and are construct-sensitive (the synthetic
proxy and the published measure are related but not identical) -- refresh them against
the latest release of each source before relying on them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Benchmark:
    metric: str
    label: str
    target: float  # approximate population share (0..1)
    tolerance: float  # absolute +/- tolerance for "within benchmark"
    source: str
    url: str
    note: str


# Sourced anchors -- see docs/REAL_DATA_PROVENANCE.md. Refresh against latest release.
PUBLIC_BENCHMARKS: list[Benchmark] = [
    Benchmark(
        metric="new_to_uk_share",
        label="Adults born outside the UK",
        target=0.168,
        tolerance=0.05,
        source="ONS Census 2021 (England & Wales)",
        url=(
            "https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/"
            "internationalmigration/bulletins/internationalmigrationenglandandwales/census2021"
        ),
        note="16.8% of England & Wales residents were born outside the UK (Census 2021).",
    ),
    Benchmark(
        metric="accessibility_need_share",
        label="Disabled adults (any long-term impairment)",
        target=0.24,
        tolerance=0.07,
        source="DWP Family Resources Survey 2022/23",
        url="https://www.gov.uk/government/statistics/family-resources-survey-financial-year-2022-to-2023",
        note="24% of the UK population (16.1m) reported a disability; definition-sensitive.",
    ),
    Benchmark(
        metric="low_digital_confidence_share",
        label="Adults with low digital capability",
        target=0.18,
        tolerance=0.06,
        source="Lloyds Consumer Digital Index 2023",
        url="https://www.lloydsbank.com/consumer-digital-index.html",
        note=(
            "~20% lack foundation digital skills (80% have them); the narrower 'confidence' "
            "proxy is anchored slightly below the skills figure. Construct-sensitive."
        ),
    ),
]
