from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.modelling.batch_score_activation import (
    run_batch_scoring,
    score_activation_frame,
    write_activation_scores,
)
from src.modelling.features import make_activation_features


class FakeBatchActivationModel:
    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        return np.linspace(0.1, 0.9, len(frame))


def _activation_frame(rows: int = 25) -> pd.DataFrame:
    return make_activation_features(
        pd.DataFrame(
            {
                "user_id": [f"user_{index:04d}" for index in range(rows)],
                "signup_date": pd.date_range("2025-06-01", periods=rows, freq="D"),
                "region": np.resize(["London", "North West", "Wales"], rows),
                "signup_channel": np.resize(["organic_search", "paid_social"], rows),
                "device_os": np.resize(["ios", "android"], rows),
                "age": np.resize([24, 37, 51, 29], rows),
                "income_segment": np.resize(["student", "middle", "high"], rows),
                "push_opt_in": np.resize([1, 0, 1], rows),
                "vulnerable_customer_flag": np.resize([0, 1, 0, 0], rows),
                "business_account_flag": np.resize([0, 0, 1], rows),
                "activated_d7": np.resize([1, 0, 1, 0], rows),
                "clv_proxy_12m_gbp": np.resize([18.0, 2.0, 24.0], rows),
            }
        )
    )


def _patch_batch_model(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.modelling.batch_score_activation.load_activation_model_artifact",
        lambda _registry_path: SimpleNamespace(
            model=FakeBatchActivationModel(),
            metadata=SimpleNamespace(
                model_version="activation-batch-test",
                threshold=0.4,
            ),
        ),
    )


def _patch_parquet_writer(monkeypatch) -> None:
    def fake_to_parquet(self: pd.DataFrame, path: Path, *, index: bool) -> None:
        Path(path).write_text(self.to_json(orient="records"), encoding="utf-8")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fake_to_parquet)


def test_activation_batch_scores_have_daily_output_contract(monkeypatch, tmp_path) -> None:
    frame = _activation_frame(rows=12)
    _patch_batch_model(monkeypatch)
    _patch_parquet_writer(monkeypatch)

    scores = score_activation_frame(
        frame,
        registry_path=tmp_path / "registry.json",
        score_date=date.fromisoformat("2025-06-30"),
    )
    output_path = write_activation_scores(
        scores,
        output_dir=tmp_path / "scores",
        score_date=date.fromisoformat("2025-06-30"),
    )

    assert output_path.name == "customer_scores_daily.parquet"
    assert output_path.parent.name == "score_date=2025-06-30"
    assert output_path.exists()
    assert len(scores) == 12
    assert set(scores["decision"]) <= {"target", "monitor"}
    assert scores["activation_probability"].between(0, 1).all()
    assert scores["model_version"].nunique() == 1
    assert scores.loc[scores["vulnerable_customer_review"], "decision"].eq("monitor").all()


def test_activation_batch_scoring_summary(monkeypatch, tmp_path) -> None:
    frame = _activation_frame()
    _patch_batch_model(monkeypatch)
    _patch_parquet_writer(monkeypatch)

    monkeypatch.setattr(
        "src.modelling.batch_score_activation.load_activation_frame",
        lambda _db_path: frame,
    )
    result = run_batch_scoring(
        db_path=tmp_path / "fake.duckdb",
        registry_path=tmp_path / "registry.json",
        output_dir=tmp_path / "scores",
        score_date=date.fromisoformat("2025-06-30"),
    )

    assert result.rows == 25
    assert result.output_path.exists()
    assert result.model_version == "activation-batch-test"
    assert result.threshold == 0.4
    assert 0 <= result.targeting_rate <= 1
