from __future__ import annotations

import pandas as pd
import pytest

from src.adapters import (
    conversion_summary,
    fairness_gaps,
    load_bank_marketing,
    prepare,
    render_markdown,
)


def _raw_uci_frame() -> pd.DataFrame:
    """A small frame in the real UCI Bank Marketing schema (column names + y target)."""
    # education 'tertiary' converts well; 'primary' poorly -> a clear fairness gap.
    converters = {
        "age": 30, "job": "admin.", "marital": "single", "education": "tertiary", "y": "yes",
    }
    non_converters = {
        "age": 70, "job": "retired", "marital": "married", "education": "primary", "y": "no",
    }
    return pd.DataFrame([converters] * 60 + [non_converters] * 60)


def test_prepare_derives_outcome_and_age_band() -> None:
    prepared = prepare(_raw_uci_frame())
    assert prepared["subscribed"].dtype == bool
    assert set(prepared["age_band"].unique()) <= {
        "under_25",
        "25_34",
        "35_44",
        "45_54",
        "55_64",
        "65_plus",
    }
    assert prepared.loc[prepared["age"] == 30, "age_band"].iloc[0] == "25_34"
    assert prepared.loc[prepared["age"] == 70, "age_band"].iloc[0] == "65_plus"


def test_prepare_requires_target_column() -> None:
    with pytest.raises(KeyError):
        prepare(pd.DataFrame({"age": [30], "job": ["admin."]}))


def test_conversion_summary() -> None:
    summary = conversion_summary(prepare(_raw_uci_frame()))
    assert summary.customers == 120
    assert summary.subscribed == 60
    assert summary.conversion_rate == pytest.approx(0.5)


def test_fairness_gaps_detects_education_disparity() -> None:
    gaps = fairness_gaps(prepare(_raw_uci_frame()), segments=["education"], min_segment_size=10)
    row = gaps[gaps["segment"] == "education"].iloc[0]
    assert row["gap_pp"] == pytest.approx(100.0)  # tertiary 100% vs primary 0%
    assert row["higher_rate_level"] == "tertiary"
    assert row["lower_rate_level"] == "primary"


def test_load_bank_marketing_reads_semicolon_csv(tmp_path) -> None:
    csv = tmp_path / "bank.csv"
    csv.write_text(
        'age;job;marital;education;y\n'
        '30;"admin.";"single";"tertiary";"yes"\n'
        '70;"retired";"married";"primary";"no"\n',
        encoding="utf-8",
    )
    frame = load_bank_marketing(csv)
    assert list(frame["subscribed"]) == [True, False]
    assert frame["age_band"].tolist() == ["25_34", "65_plus"]


def test_render_markdown_reports_conversion_and_gaps() -> None:
    md = render_markdown(prepare(_raw_uci_frame()))
    assert "UCI Bank Marketing" in md
    assert "conversion" in md.lower()
    assert "Moro et al. 2014" in md


def test_fairness_gaps_empty_frame() -> None:
    assert fairness_gaps(pd.DataFrame()).empty
