from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.adapters.criteo_uplift import (
    experiment_readout,
    load_criteo,
    prepare,
    render_markdown,
)


def _raw_criteo_frame(n: int = 2_000) -> pd.DataFrame:
    """A small frame in the real Criteo Uplift schema with a genuine treatment effect.

    ``f0`` is a pre-randomisation feature correlated with the outcome (so CUPED has
    something to work with); treatment lifts conversion by a fixed amount.
    """
    rng = np.random.default_rng(7)
    treatment = rng.integers(0, 2, size=n)
    f0 = rng.normal(0.0, 1.0, size=n)
    base = 0.10 + 0.05 * (f0 > 0)  # covariate shifts the baseline rate
    prob = np.clip(base + 0.04 * treatment, 0, 1)
    conversion = (rng.random(n) < prob).astype(int)
    visit = (rng.random(n) < prob + 0.2).astype(int)
    return pd.DataFrame(
        {
            "treatment": treatment,
            "conversion": conversion,
            "visit": visit,
            "exposure": treatment,
            "f0": f0,
            "f1": rng.normal(size=n),
        }
    )


def test_prepare_maps_treatment_to_variant() -> None:
    prepared = prepare(_raw_criteo_frame(50))
    assert set(prepared["variant"].unique()) <= {"control", "treatment"}
    assert prepared["conversion"].dtype == float
    assert "f0" in prepared.columns


def test_prepare_requires_treatment_column() -> None:
    with pytest.raises(KeyError):
        prepare(pd.DataFrame({"conversion": [0, 1], "f0": [0.1, 0.2]}))


def test_prepare_requires_an_outcome_column() -> None:
    with pytest.raises(KeyError):
        prepare(pd.DataFrame({"treatment": [0, 1], "f0": [0.1, 0.2]}))


def test_experiment_readout_runs_platform_estimators() -> None:
    readout = experiment_readout(prepare(_raw_criteo_frame()), metric="conversion")
    # Naive and CUPED both estimate a positive-ish lift; the fixture embeds +4pp.
    assert readout.naive.control_n > 0 and readout.naive.treatment_n > 0
    assert readout.cuped.covariate_mean == pytest.approx(
        prepare(_raw_criteo_frame())["f0"].mean(), rel=1e-6
    )
    # CUPED should not blow up variance; with a correlated covariate it reduces it.
    assert readout.cuped.variance_reduction >= 0.0
    assert readout.srm.counts["control"] + readout.srm.counts["treatment"] == 2_000


def test_auto_covariate_selects_a_feature() -> None:
    readout = experiment_readout(prepare(_raw_criteo_frame()), covariate="auto")
    assert readout.covariate in {"f0", "f1"}


def test_render_markdown_flags_adtech_boundary() -> None:
    md = render_markdown(experiment_readout(prepare(_raw_criteo_frame())), records=2_000)
    assert "Criteo Uplift" in md
    # The mandatory honest caveat must be present.
    assert "no known ground-truth lift" in md.lower()
    assert "CUPED" in md


def test_load_criteo_reads_comma_csv_with_sampling(tmp_path) -> None:
    csv = tmp_path / "criteo.csv"
    _raw_criteo_frame(500).to_csv(csv, index=False)
    frame = load_criteo(csv, sample_rows=100)
    assert len(frame) == 100
    assert set(frame["variant"].unique()) <= {"control", "treatment"}
