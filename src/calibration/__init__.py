"""Public-data calibration for the synthetic generators.

Anchors the synthetic wellbeing / inclusion distributions to approximate UK public
benchmarks so reviewers can see how realistic the simulation is and where the
generators should be tuned. The benchmark values are *illustrative anchors* and must
be verified and updated against the cited source before any real-world use.
"""

from src.calibration.benchmarks import PUBLIC_BENCHMARKS, Benchmark
from src.calibration.calibrate import (
    CalibrationResult,
    calibrate,
    measure_synthetic,
    render_markdown,
)

__all__ = [
    "PUBLIC_BENCHMARKS",
    "Benchmark",
    "CalibrationResult",
    "calibrate",
    "measure_synthetic",
    "render_markdown",
]
