from __future__ import annotations

import numpy as np
import pandas as pd

from src.modelling.evaluate import (
    choose_threshold,
    classification_metrics,
    customer_outcome_guardrails,
    threshold_sweep,
)
from src.modelling.explain import coefficient_importance
from src.modelling.features import (
    activated_user_value,
    feature_matrix,
    make_activation_features,
    target_vector,
    temporal_train_calibration_test_split,
)
from src.modelling.run_activation_model import render_model_card, train_and_evaluate
from src.modelling.train import fit_calibrated_activation_model


def _activation_frame(rows: int = 900) -> pd.DataFrame:
    rng = np.random.default_rng(13)
    signup_dates = pd.date_range("2025-01-01", periods=rows, freq="D")
    channels = rng.choice(["word_of_mouth", "paid_social", "app_store"], size=rows)
    income = rng.choice(["low", "middle", "high"], size=rows)
    push = rng.binomial(1, 0.65, size=rows)
    vulnerable = rng.binomial(1, 0.06, size=rows)
    business = rng.binomial(1, 0.08, size=rows)
    score = (
        0.42
        + np.where(channels == "word_of_mouth", 0.12, 0)
        - np.where(channels == "paid_social", 0.07, 0)
        + np.where(income == "high", 0.07, 0)
        + push * 0.05
        + business * 0.03
        - vulnerable * 0.05
    )
    activated = rng.binomial(1, np.clip(score, 0.05, 0.90))
    return make_activation_features(
        pd.DataFrame(
            {
                "user_id": [f"user_{index:04d}" for index in range(rows)],
                "signup_date": signup_dates,
                "region": rng.choice(["London", "North West", "Wales"], size=rows),
                "signup_channel": channels,
                "device_os": rng.choice(["ios", "android"], size=rows),
                "age": rng.integers(18, 70, size=rows),
                "income_segment": income,
                "push_opt_in": push,
                "vulnerable_customer_flag": vulnerable,
                "business_account_flag": business,
                "activated_d7": activated,
                "clv_proxy_12m_gbp": np.where(activated == 1, 22.0, 2.0),
            }
        )
    )


def test_temporal_split_preserves_order_and_sizes() -> None:
    frame = _activation_frame()

    split = temporal_train_calibration_test_split(frame)

    assert len(split.train) == 540
    assert len(split.calibration) == 180
    assert len(split.test) == 180
    assert split.train["signup_date"].max() <= split.calibration["signup_date"].min()
    assert split.calibration["signup_date"].max() <= split.test["signup_date"].min()


def test_calibrated_model_outputs_probabilities_and_explanations() -> None:
    frame = _activation_frame()
    split = temporal_train_calibration_test_split(frame)

    model = fit_calibrated_activation_model(split.train, split.calibration)
    probabilities = model.predict_proba(feature_matrix(split.test))
    importance = coefficient_importance(model, top_n=5)

    assert len(probabilities) == len(split.test)
    assert np.all((probabilities >= 0) & (probabilities <= 1))
    assert list(importance.columns) == ["feature", "coefficient", "absolute_coefficient"]


def test_metrics_thresholds_and_guardrails_are_computable() -> None:
    frame = _activation_frame()
    split = temporal_train_calibration_test_split(frame)
    model = fit_calibrated_activation_model(split.train, split.calibration)
    probabilities = model.predict_proba(feature_matrix(split.test))

    metrics = classification_metrics(target_vector(split.test), probabilities)
    thresholds = threshold_sweep(
        split.test,
        probabilities,
        value_per_activation_gbp=activated_user_value(split.train),
    )
    threshold = choose_threshold(thresholds)
    guardrails = customer_outcome_guardrails(split.test, probabilities, threshold.threshold)

    assert 0 <= metrics.expected_calibration_error <= 1
    assert threshold.targeted_users > 0
    assert len(guardrails) == 3


def test_model_card_renders_from_real_run(monkeypatch, tmp_path) -> None:
    frame = _activation_frame()

    def fake_load(_db_path):
        return frame

    monkeypatch.setattr("src.modelling.run_activation_model.load_activation_frame", fake_load)

    run, _model = train_and_evaluate(tmp_path / "fake.duckdb")
    card = render_model_card(run)

    assert "Model Card: Activation Decisioning" in card
    assert "Customer-Outcome Guardrails" in card
    assert run.rows == len(frame)
