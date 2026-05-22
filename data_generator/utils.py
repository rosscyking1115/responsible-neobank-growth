from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl


def month_end(start_date: date, months: int) -> date:
    month_index = start_date.month - 1 + months
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1) - timedelta(days=1)


def sigmoid(value: float | np.ndarray) -> float | np.ndarray:
    return 1 / (1 + np.exp(-value))


def stable_bucket(value: str, modulo: int = 10_000) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo


def ensure_output_dir(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_parquet(frame: pl.DataFrame, output_dir: Path, name: str) -> None:
    frame.write_parquet(output_dir / f"{name}.parquet")


def random_datetimes_within_days(
    rng: np.random.Generator,
    start: datetime,
    days: np.ndarray,
) -> list[datetime]:
    seconds = rng.integers(0, 86_400, size=len(days))
    return [
        start + timedelta(days=int(day), seconds=int(second))
        for day, second in zip(days, seconds, strict=True)
    ]


def date_range_days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
