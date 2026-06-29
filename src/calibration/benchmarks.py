"""Public benchmark anchors for calibrating the synthetic population.

IMPORTANT: the ``target`` values below are *approximate, illustrative anchors* drawn
from well-known UK public sources. They are intended to make the synthetic data
defensible and to show where the generators diverge from reality -- they are NOT
authoritative figures. Verify and update each value against the cited source (and its
latest release) before relying on it.
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


# Approximate anchors -- verify against source before real-world use.
PUBLIC_BENCHMARKS: list[Benchmark] = [
    Benchmark(
        metric="new_to_uk_share",
        label="Adults born outside the UK",
        target=0.16,
        tolerance=0.05,
        source="ONS Census 2021 (England & Wales)",
        url="https://www.ons.gov.uk",
        note="Proxy for new-to-UK customers; verify the latest ONS figure and geography.",
    ),
    Benchmark(
        metric="accessibility_need_share",
        label="Disabled adults (any long-term impairment)",
        target=0.20,
        tolerance=0.07,
        source="DWP Family Resources Survey",
        url="https://www.gov.uk",
        note="Proxy for accessibility needs; highly definition-sensitive, verify.",
    ),
    Benchmark(
        metric="low_digital_confidence_share",
        label="Adults lacking foundation digital skills",
        target=0.07,
        tolerance=0.04,
        source="Lloyds Consumer Digital Index / ONS",
        url="https://www.lloydsbank.com",
        note="Proxy for low digital confidence; verify the latest published figure.",
    ),
]
