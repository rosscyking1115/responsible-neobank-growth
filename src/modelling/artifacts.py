"""Persist and load activation model artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import joblib

from src.modelling.train import CalibratedActivationModel

if TYPE_CHECKING:
    from src.modelling.run_activation_model import ActivationModelRun

DEFAULT_ACTIVATION_ARTIFACT_DIR = Path("artifacts/models/activation")
REGISTRY_FILENAME = "registry.json"
MODEL_FILENAME = "model.joblib"
METADATA_FILENAME = "metadata.json"


@dataclass(frozen=True)
class ActivationModelMetadata:
    model_version: str
    model_path: str
    threshold: float
    feature_columns: list[str]
    trained_at: str
    rows: int
    train_rows: int
    calibration_rows: int
    test_rows: int
    metrics: dict[str, Any]
    guardrails: list[dict[str, Any]]


@dataclass(frozen=True)
class ActivationModelBundle:
    model: CalibratedActivationModel
    metadata: ActivationModelMetadata


def _model_version() -> str:
    return f"activation-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"


def write_activation_model_artifact(
    model: CalibratedActivationModel,
    run: ActivationModelRun,
    artifact_dir: Path = DEFAULT_ACTIVATION_ARTIFACT_DIR,
    *,
    model_version: str | None = None,
) -> ActivationModelMetadata:
    version = model_version or _model_version()
    version_dir = artifact_dir / version
    version_dir.mkdir(parents=True, exist_ok=True)

    model_path = version_dir / MODEL_FILENAME
    metadata_path = version_dir / METADATA_FILENAME
    joblib.dump(model, model_path)

    metadata = ActivationModelMetadata(
        model_version=version,
        model_path=f"{version}/{MODEL_FILENAME}",
        threshold=run.threshold.threshold,
        feature_columns=model.feature_columns,
        trained_at=datetime.now(UTC).isoformat(),
        rows=run.rows,
        train_rows=run.train_rows,
        calibration_rows=run.calibration_rows,
        test_rows=run.test_rows,
        metrics=asdict(run.metrics),
        guardrails=[asdict(check) for check in run.guardrails],
    )
    metadata_path.write_text(
        json.dumps(asdict(metadata), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    registry = {
        "active_model_version": version,
        "models": {
            version: asdict(metadata),
        },
    }
    registry_path = artifact_dir / REGISTRY_FILENAME
    if registry_path.exists():
        existing = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["models"] = {**existing.get("models", {}), version: asdict(metadata)}
    registry_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return metadata


def load_activation_model_artifact(registry_path: Path) -> ActivationModelBundle:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    active_version = registry["active_model_version"]
    raw_metadata = registry["models"][active_version]
    metadata = ActivationModelMetadata(**raw_metadata)
    artifact_dir = registry_path.parent
    model = joblib.load(artifact_dir / metadata.model_path)
    return ActivationModelBundle(model=model, metadata=metadata)
