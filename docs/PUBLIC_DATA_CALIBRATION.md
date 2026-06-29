# Public-Data Calibration

Synthetic data is only credible if its distributions are plausible. This module
**anchors the synthetic wellbeing / inclusion population to approximate UK public
benchmarks**, measures the generated data against them, and reports the gaps — so a
reviewer can see how realistic the simulation is and where the generators should be
tuned.

> **The benchmark targets are approximate, illustrative anchors** drawn from
> well-known UK public sources. They are seeded to make the project defensible and to
> demonstrate the calibration workflow — they are **not authoritative figures**.
> Verify and update each value against the cited source (and its latest release)
> before relying on it.

## Where it lives

| Concern | Location |
| --- | --- |
| Benchmark anchors (with sources) | [`src/calibration/benchmarks.py`](../src/calibration/benchmarks.py) |
| Measure + compare + report | [`src/calibration/calibrate.py`](../src/calibration/calibrate.py) |
| Tests | [`tests/test_calibration.py`](../tests/test_calibration.py) |

## Anchors

| Metric | Synthetic proxy | Source (verify) |
| --- | --- | --- |
| Adults born outside the UK | `new_to_uk_proxy` | ONS Census 2021 |
| Disabled adults (any long-term impairment) | `accessibility_need_proxy` | DWP Family Resources Survey |
| Adults lacking foundation digital skills | low `digital_confidence_band` | Lloyds Consumer Digital Index / ONS |

## Run it

```powershell
uv run python -m src.calibration.calibrate --db neobank.duckdb
```

Example output (default 5k-user demo):

```text
| Metric                                    | Observed | Benchmark | Within? |
| Adults born outside the UK                |   14.6%  |   16.0%   |   yes   |
| Disabled adults (any long-term impairment)|   16.7%  |   20.0%   |   yes   |
| Adults lacking foundation digital skills  |    6.5%  |    7.0%   |   yes   |
```

The wellbeing generator in
[`data_generator/wellbeing.py`](../data_generator/wellbeing.py) has been **tuned to
these anchors** (base rates for new-to-UK, accessibility need, and the digital-
confidence intercept/spread), so the measured shares now fall within tolerance. The
report stays in the toolkit as a regression check: if a generator change or an updated
anchor pushes a metric out of tolerance, it shows up here as a `NO`.

## Boundary

This calibrates *aggregate distributions* of synthetic proxies against public
aggregates. It uses no real customer-level data and produces no individual inferences.
