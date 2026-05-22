"""Model training utilities."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.modelling.features import (
    BINARY_FEATURES,
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    feature_matrix,
    target_vector,
)


@dataclass
class CalibratedActivationModel:
    """Signup-time activation propensity model with a separate probability calibrator."""

    estimator: Pipeline
    calibrator: IsotonicRegression
    feature_columns: list[str]

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        raw_scores = self.estimator.predict_proba(frame[self.feature_columns])[:, 1]
        return self.calibrator.predict(raw_scores)


def build_activation_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            ("binary", "passthrough", BINARY_FEATURES),
        ],
        remainder="drop",
    )
    classifier = LogisticRegression(max_iter=1_000, class_weight="balanced")
    return Pipeline([("preprocessor", preprocessor), ("classifier", classifier)])


def fit_calibrated_activation_model(
    train_frame: pd.DataFrame,
    calibration_frame: pd.DataFrame,
    *,
    estimator: BaseEstimator | None = None,
) -> CalibratedActivationModel:
    """Fit the base model on historical users and calibrate on the next time window."""

    base_estimator = estimator or build_activation_pipeline()
    base_estimator.fit(feature_matrix(train_frame), target_vector(train_frame))
    calibration_scores = base_estimator.predict_proba(feature_matrix(calibration_frame))[:, 1]
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(calibration_scores, target_vector(calibration_frame))
    return CalibratedActivationModel(
        estimator=base_estimator,
        calibrator=calibrator,
        feature_columns=FEATURE_COLUMNS,
    )
