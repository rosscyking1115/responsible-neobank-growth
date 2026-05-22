"""Explainability helpers for model outputs."""

from __future__ import annotations

import pandas as pd

from src.modelling.train import CalibratedActivationModel


def coefficient_importance(model: CalibratedActivationModel, *, top_n: int = 15) -> pd.DataFrame:
    """Return largest absolute logistic coefficients after one-hot encoding."""

    preprocessor = model.estimator.named_steps["preprocessor"]
    classifier = model.estimator.named_steps["classifier"]
    feature_names = preprocessor.get_feature_names_out()
    coefficients = classifier.coef_[0]
    frame = pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": coefficients,
            "absolute_coefficient": abs(coefficients),
        }
    )
    return frame.sort_values("absolute_coefficient", ascending=False).head(top_n).reset_index(
        drop=True
    )


def segment_score_summary(
    frame: pd.DataFrame,
    probabilities,
    segment: str,
    *,
    min_rows: int = 250,
) -> pd.DataFrame:
    scored = frame[[segment, "activated_d7"]].copy()
    scored["activation_probability"] = probabilities
    rows = (
        scored.groupby(segment)
        .agg(
            rows=("activation_probability", "size"),
            mean_score=("activation_probability", "mean"),
            activation_rate=("activated_d7", "mean"),
        )
        .reset_index()
    )
    rows = rows.loc[rows["rows"] >= min_rows].copy()
    return rows.sort_values("mean_score", ascending=False).reset_index(drop=True)
