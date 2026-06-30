# Public-Data Calibration

Synthetic data is only credible if its distributions are plausible. This module
**anchors the synthetic wellbeing / inclusion population to real UK public
benchmarks**, measures the generated data against them, and reports the gaps — so a
reviewer can see how realistic the simulation is.

> The benchmark targets are taken from named UK public sources (ONS, DWP, Lloyds) —
> see [REAL_DATA_PROVENANCE.md](REAL_DATA_PROVENANCE.md) for the full citations,
> figures, and construct notes. They are point-in-time and construct-sensitive;
> refresh them against the latest release of each source.

## Where it lives

| Concern | Location |
| --- | --- |
| Benchmark anchors (with sources) | [`src/calibration/benchmarks.py`](../src/calibration/benchmarks.py) |
| Measure + compare + report | [`src/calibration/calibrate.py`](../src/calibration/calibrate.py) |
| Tests | [`tests/test_calibration.py`](../tests/test_calibration.py) |

## Anchors

| Metric | Synthetic proxy | Benchmark | Source (year) |
| --- | --- | ---: | --- |
| Adults born outside the UK | `new_to_uk_proxy` | 16.8% | ONS Census 2021 |
| Disabled adults (any long-term impairment) | `accessibility_need_proxy` | 24% | DWP Family Resources Survey 2022/23 |
| Adults with low digital capability | low `digital_confidence_band` | 18% | Lloyds Consumer Digital Index 2023 |

## Run it

```powershell
uv run python -m src.calibration.calibrate --db neobank.duckdb
```

Example output (default 5k-user demo):

```text
| Metric                                    | Observed | Benchmark | Within? |
| Adults born outside the UK                |   15.7%  |   16.8%   |   yes   |
| Disabled adults (any long-term impairment)|   21.3%  |   24.0%   |   yes   |
| Adults with low digital capability        |   16.1%  |   18.0%   |   yes   |
```

The wellbeing generator in
[`data_generator/wellbeing.py`](../data_generator/wellbeing.py) has been **tuned to
these anchors** (base rates for new-to-UK and accessibility need, and the digital-
confidence intercept/spread), so the measured shares fall within tolerance. The report
stays in the toolkit as a regression check: if a generator change or an updated anchor
pushes a metric out of tolerance, it shows up here as a `NO`.

## Boundary

This calibrates *aggregate distributions* of synthetic proxies against public
aggregates. It uses no real customer-level data and produces no individual inferences.
