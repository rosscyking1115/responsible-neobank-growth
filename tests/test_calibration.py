from __future__ import annotations

import pandas as pd
import pytest

from src.calibration import (
    PUBLIC_BENCHMARKS,
    Benchmark,
    calibrate,
    measure_synthetic,
    render_markdown,
)


def _frame(n: int = 100) -> pd.DataFrame:
    # ~17% new-to-UK, 24% accessibility need, 18% low digital confidence (within the
    # verified benchmark tolerances).
    return pd.DataFrame(
        {
            "new_to_uk_proxy": [True] * 17 + [False] * 83,
            "accessibility_need_proxy": [True] * 24 + [False] * 76,
            "digital_confidence_band": ["low"] * 18 + ["medium"] * 42 + ["high"] * 40,
        }
    )


def test_benchmarks_are_well_formed() -> None:
    assert PUBLIC_BENCHMARKS
    for b in PUBLIC_BENCHMARKS:
        assert 0.0 <= b.target <= 1.0
        assert b.tolerance > 0
        assert b.source and b.url


def test_measure_synthetic_computes_shares() -> None:
    observed = measure_synthetic(_frame())
    assert observed["new_to_uk_share"] == pytest.approx(0.17)
    assert observed["accessibility_need_share"] == pytest.approx(0.24)
    assert observed["low_digital_confidence_share"] == pytest.approx(0.18)


def test_calibrate_flags_within_tolerance() -> None:
    results = {r.metric: r for r in calibrate(_frame())}
    # The crafted frame matches the default anchors exactly.
    assert results["new_to_uk_share"].within
    assert results["accessibility_need_share"].within
    assert results["low_digital_confidence_share"].within


def test_calibrate_flags_out_of_tolerance() -> None:
    frame = _frame().assign(new_to_uk_proxy=[False] * 100)  # 0% vs 16% benchmark
    result = next(r for r in calibrate(frame) if r.metric == "new_to_uk_share")
    assert not result.within
    assert result.deviation < 0


def test_calibrate_respects_custom_benchmarks() -> None:
    custom = [
        Benchmark(
            metric="low_digital_confidence_share",
            label="Low digital confidence",
            target=0.50,
            tolerance=0.02,
            source="test",
            url="https://example.com",
            note="test",
        )
    ]
    result = calibrate(_frame(), custom)[0]
    assert result.target == 0.50
    assert not result.within  # observed 18% vs 50%


def test_measure_synthetic_handles_empty_and_missing_columns() -> None:
    assert measure_synthetic(pd.DataFrame()) == {}
    partial = pd.DataFrame({"new_to_uk_proxy": [True, False]})
    observed = measure_synthetic(partial)
    assert "new_to_uk_share" in observed
    assert "accessibility_need_share" not in observed


def test_render_markdown_includes_disclaimer_and_rows() -> None:
    md = render_markdown(calibrate(_frame()))
    assert "Public-Data Calibration" in md
    assert "named UK public sources" in md
    assert "Adults born outside the UK" in md
