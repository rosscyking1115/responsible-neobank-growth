"""Batch score activation propensity from a persisted activation model registry."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.modelling.artifacts import REGISTRY_FILENAME, load_activation_model_artifact
from src.modelling.features import feature_matrix, load_activation_frame

DEFAULT_SCORE_OUTPUT_DIR = Path("artifacts/scoring/activation")


@dataclass(frozen=True)
class BatchScoringResult:
    output_path: Path
    rows: int
    score_date: date
    model_version: str
    threshold: float
    targeted_users: int
    targeting_rate: float
    vulnerable_review_users: int


def score_activation_frame(
    frame: pd.DataFrame,
    *,
    registry_path: Path,
    score_date: date,
) -> pd.DataFrame:
    bundle = load_activation_model_artifact(registry_path)
    probabilities = bundle.model.predict_proba(feature_matrix(frame))
    threshold = float(bundle.metadata.threshold)
    vulnerable = frame["vulnerable_customer_flag"].astype(bool).to_numpy()
    target = (probabilities <= threshold) & ~vulnerable
    needs_review = (probabilities <= threshold) & vulnerable

    return pd.DataFrame(
        {
            "score_date": pd.to_datetime(score_date),
            "user_id": frame["user_id"].astype(str).to_numpy(),
            "signup_date": pd.to_datetime(frame["signup_date"]).to_numpy(),
            "model_version": bundle.metadata.model_version,
            "activation_probability": np.round(probabilities, 6),
            "activation_threshold": threshold,
            "decision": np.where(target, "target", "monitor"),
            "vulnerable_customer_review": needs_review,
            "income_segment": frame["income_segment"].astype(str).to_numpy(),
            "signup_channel": frame["signup_channel"].astype(str).to_numpy(),
            "region": frame["region"].astype(str).to_numpy(),
        }
    )


def write_activation_scores(
    scores: pd.DataFrame,
    *,
    output_dir: Path,
    score_date: date,
) -> Path:
    partition_dir = output_dir / f"score_date={score_date.isoformat()}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    output_path = partition_dir / "customer_scores_daily.parquet"
    scores.to_parquet(output_path, index=False)
    return output_path


def run_batch_scoring(
    *,
    db_path: Path,
    registry_path: Path,
    output_dir: Path = DEFAULT_SCORE_OUTPUT_DIR,
    score_date: date | None = None,
) -> BatchScoringResult:
    effective_score_date = score_date or datetime.now(UTC).date()
    frame = load_activation_frame(db_path)
    scores = score_activation_frame(
        frame,
        registry_path=registry_path,
        score_date=effective_score_date,
    )
    output_path = write_activation_scores(
        scores,
        output_dir=output_dir,
        score_date=effective_score_date,
    )
    target = scores["decision"] == "target"
    vulnerable_review = scores["vulnerable_customer_review"].astype(bool)
    return BatchScoringResult(
        output_path=output_path,
        rows=len(scores),
        score_date=effective_score_date,
        model_version=str(scores["model_version"].iloc[0]),
        threshold=float(scores["activation_threshold"].iloc[0]),
        targeted_users=int(target.sum()),
        targeting_rate=float(target.mean()),
        vulnerable_review_users=int(vulnerable_review.sum()),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch score activation propensity.")
    parser.add_argument("--db", type=Path, default=Path("neobank.duckdb"))
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("artifacts/models/activation") / REGISTRY_FILENAME,
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_SCORE_OUTPUT_DIR)
    parser.add_argument("--score-date", type=date.fromisoformat, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_batch_scoring(
        db_path=args.db,
        registry_path=args.registry,
        output_dir=args.output_dir,
        score_date=args.score_date,
    )
    print(
        "Wrote "
        f"{result.rows:,} activation scores to {result.output_path} "
        f"using {result.model_version}; targeted {result.targeted_users:,} users "
        f"({result.targeting_rate:.2%})."
    )


if __name__ == "__main__":
    main()
